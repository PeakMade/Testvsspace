"""
Flask Web App for Entrata Lease Reports
Interactive app to select academic years and lease status types
"""
from flask import Flask, render_template, request, jsonify, send_file, Response, make_response
import os
import requests
import pandas as pd
from datetime import datetime, timedelta, date as date_type
from dotenv import load_dotenv
import json
import io
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import calendar
import openpyxl.styles

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
PROPERTIES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

# Progress tracking
progress_data = {}
report_results = {}
progress_lock = threading.Lock()

# Parallel processing settings
MAX_WORKERS = 10  # Number of concurrent API requests

# Lease status types
LEASE_STATUSES = {
    '1': 'Pending',
    '2': 'Denied',
    '3': 'Approved',
    '4': 'Current',
    '5': 'Notice',
    '6': 'Past',
    '7': 'Cancelled'
}

# Entrata API has a hard 500-record limit per request
# We use date-range bisection to bypass this cap


def get_all_properties():
    """Get all properties from Entrata API"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getProperties",
            "version": "r1",
            "params": {}
        }
    }
    
    try:
        response = requests.post(PROPERTIES_URL, headers=headers, json=payload, timeout=60)
        data = response.json()
        
        if 'error' in data.get('response', {}):
            return []
        
        result = data.get('response', {}).get('result', {})
        physical_property = result.get('PhysicalProperty', {})
        properties = physical_property.get('Property', [])
        
        if isinstance(properties, dict):
            properties = [properties]
        
        # Filter to only active residential properties (excluding Canadian)
        filtered_properties = []
        exclude_keywords = ['retail', 'reit', 'llc', 'corporate', 'shuttle', 'condominium', 'assoc', 'master', 'ucc', 'university center', 'gateway', 'connect', 'member', ' lp', ' pe']
        exclude_countries = ['CAN']
        
        for prop in properties:
            prop_name = prop.get('MarketingName', '')
            is_disabled = prop.get('IsDisabled', 0)
            prop_type = prop.get('Type', '')
            
            # Skip disabled properties
            if is_disabled == 1:
                continue
            
            # Skip Corporate type properties (vendors)
            if prop_type == 'Corporate':
                continue
            
            # Skip if no valid property name
            if not prop_name or prop_name.strip() == '':
                continue
            
            # Skip properties starting with 'z' or 'Z' (archived)
            if prop_name.startswith('z') or prop_name.startswith('Z'):
                continue
            
            # Skip if name contains excluded keywords (case-insensitive)
            if any(keyword in prop_name.lower() for keyword in exclude_keywords):
                continue
            
            address = prop.get('Address', {})
            country = address.get('Country', '')
            if country in exclude_countries:
                continue
            
            # Skip placeholder properties that never went live (no operational indicators)
            has_operational_data = (
                prop.get('YearBuilt') or 
                prop.get('PropertyHours') or 
                prop.get('webSite') or
                prop.get('LongDescription') or
                prop.get('ShortDescription') or
                prop.get('LeaseTerms')
            )
            if not has_operational_data:
                continue
            
            filtered_properties.append(prop)
        
        return filtered_properties
        
    except Exception as e:
        print(f"Error getting properties: {e}")
        return []


def _extract_leases_from_result(result):
    """Pull the lease list out of an Entrata result dict."""
    leases = []
    if 'leases' in result:
        ld = result['leases']
        leases = ld.get('lease', []) if isinstance(ld, dict) else ld
    elif 'Leases' in result:
        ld = result['Leases']
        leases = ld.get('Lease', []) if isinstance(ld, dict) else ld
    elif 'lease' in result:
        leases = result['lease']
    elif 'Lease' in result:
        leases = result['Lease']
    if isinstance(leases, dict):
        leases = [leases]
    return leases or []


_ENTRATA_CAP = 500  # Entrata's hard per-request record limit


def _query_ids_in_range(headers, property_id, date_from, date_to, status_ids):
    """Query lease IDs for a property within a moveInDate range.
    Returns a list of ID strings, or None on API error."""
    params = {
        "propertyId": str(property_id),
        "leaseStatusTypeIds": status_ids,
        "moveInDateFrom": date_from.strftime("%m/%d/%Y"),
        "moveInDateTo": date_to.strftime("%m/%d/%Y"),
    }
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {"name": "getLeases", "version": "r2", "params": params}
    }
    try:
        resp = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()
        if 'error' in data.get('response', {}):
            return None
        result = data.get('response', {}).get('result', {})
        leases = _extract_leases_from_result(result)
        return [str(l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') or '') 
                for l in leases if (l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id'))]
    except Exception:
        return None


def _collect_all_ids(headers, property_id, date_from, date_to, status_ids, depth=0):
    """Recursively collect all unique lease IDs, bisecting the date range
    whenever the API returns exactly 500 records (the hard cap).
    Continues splitting until every sub-range is below the cap."""
    
    ids = _query_ids_in_range(headers, property_id, date_from, date_to, status_ids)
    if ids is None:
        return set()
    
    if len(ids) < _ENTRATA_CAP:
        # Under the cap — we have all records in this range
        if depth == 0:
            print(f"    {len(ids)} leases")
        return set(ids)
    
    # Hit the cap! Log warning and bisect
    indent = "  " * (depth + 2)
    print(f"{indent}⚠️  Hit 500-record cap for range {date_from} to {date_to} - bisecting...")
    
    if date_from >= date_to:
        # Single day still hitting the cap - this means data loss!
        print(f"{indent}🚨 CRITICAL: Single-day range {date_from} STILL at 500 cap!")
        print(f"{indent}   Property {property_id} has 500+ leases on this ONE DAY")
        print(f"{indent}   DATA MAY BE INCOMPLETE - consider narrowing filters")
        return set(ids)
    
    # Hit the cap; bisect and take the union of both halves
    mid = date_from + (date_to - date_from) // 2
    left  = _collect_all_ids(headers, property_id, date_from, mid, status_ids, depth + 1)
    right = _collect_all_ids(headers, property_id, mid + timedelta(days=1), date_to, status_ids, depth + 1)
    combined = left | right
    
    if depth == 0:
        print(f"    ✓ Bisection complete: {len(combined)} unique lease IDs")
    
    return combined


def _query_all_leases_bisection(headers, property_id, date_from, date_to, status_ids):
    """Query all lease IDs for a property using date-range bisection to bypass the 500 cap.
    Returns a set of unique ID strings."""
    all_ids = _collect_all_ids(headers, property_id, date_from, date_to, status_ids)
    
    if len(all_ids) == 0:
        print(f"    No leases found for status {status_ids}")
    
    return all_ids


def get_leases_for_property_by_status(property_id, property_name, academic_years, status_ids_list):
    """Get count of leases for specified academic years by each status.
    Queries month-by-month upfront to avoid hitting 500 cap.
    Bisection only triggers as safety net if a single month has 500+ leases.
    Returns a dictionary with counts for each status."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    
    status_counts = {}
    
    # Query each status separately
    for status_id in status_ids_list:
        total_ids = set()
        
        for year in academic_years:
            # Academic year: August (year) to July (year+1)
            months = [
                (year, 8), (year, 9), (year, 10), (year, 11), (year, 12),
                (year + 1, 1), (year + 1, 2), (year + 1, 3), (year + 1, 4),
                (year + 1, 5), (year + 1, 6), (year + 1, 7)
            ]
            
            for month_year, month_num in months:
                # First day of month
                month_start = date_type(month_year, month_num, 1)
                
                # Last day of month
                last_day = calendar.monthrange(month_year, month_num)[1]
                month_end = date_type(month_year, month_num, last_day)
                
                month_ids = _query_all_leases_bisection(
                    headers, property_id,
                    month_start,
                    month_end,
                    status_id
                )
                total_ids.update(month_ids)
        
        status_name = LEASE_STATUSES[status_id]
        status_counts[status_name] = len(total_ids)
    
    return status_counts


@app.route('/')
def index():
    """Main page with form"""
    # Generate list of academic years (current +/- 5 years)
    today = date_type.today()
    current_year = today.year if today.month < 8 else today.year
    
    years = list(range(current_year - 2, current_year + 6))
    
    response = make_response(render_template('index.html', 
                         years=years, 
                         statuses=LEASE_STATUSES,
                         current_year=current_year))
    
    # Prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@app.route('/run_report', methods=['POST'])
def run_report():
    """Run the report with selected parameters and return task ID"""
    data = request.get_json()
    selected_year = data.get('year')
    selected_statuses = data.get('statuses', [])
    
    if not selected_year or not selected_statuses:
        return jsonify({'error': 'Please select a year and at least one status'}), 400
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Initialize progress
    progress_data[task_id] = {
        'status': 'starting',
        'current': 0,
        'total': 0,
        'current_property': 'Initializing...',
        'message': 'Starting report generation'
    }
    
    # Start background thread to process report
    thread = threading.Thread(target=process_report, args=(task_id, selected_year, selected_statuses))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})


def process_report(task_id, selected_year, selected_statuses):
    """Process the report in background and track progress"""
    try:
        report_start_time = datetime.now()
        print(f"\n{'#'*80}")
        print(f"NEW REPORT REQUEST - {report_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Task ID: {task_id}")
        print(f"{'#'*80}")
        
        selected_years = [int(selected_year)]
        
        # Store selected status IDs as list for separate queries
        status_ids_list = selected_statuses
        status_names = ', '.join([LEASE_STATUSES[s] for s in selected_statuses])
        year_display = f"{selected_years[0]}-{selected_years[0] + 1}"
        
        # Get all properties
        progress_data[task_id]['message'] = 'Fetching properties from Entrata API...'
        print(f"\nFetching properties from Entrata API...")
        prop_start = datetime.now()
        properties = get_all_properties()
        prop_elapsed = (datetime.now() - prop_start).total_seconds()
        print(f"✓ Retrieved {len(properties)} properties ({prop_elapsed:.2f} seconds)")
        
        if not properties:
            progress_data[task_id]['status'] = 'error'
            progress_data[task_id]['message'] = 'Could not retrieve properties'
            return
        
        # Update progress with total
        progress_data[task_id]['total'] = len(properties)
        progress_data[task_id]['status'] = 'processing'
        
        results = []
        completed_count = [0]  # Using list to allow modification in nested function
        
        print(f"\n{'='*80}")
        print(f"PROCESSING {len(properties)} PROPERTIES (Using {MAX_WORKERS} parallel workers)")
        print(f"Academic Year: {year_display}")
        print(f"Status Types: {status_names}")
        print(f"{'='*80}\n")
        
        def process_single_property(prop, index):
            """Process a single property and return results"""
            prop_id = prop.get('PropertyID')
            prop_name = prop.get('MarketingName', f"Property {prop_id}")
            
            print(f"[{index}/{len(properties)}] Processing: {prop_name} (ID: {prop_id})")
            start_time = datetime.now()
            
            status_counts = get_leases_for_property_by_status(prop_id, prop_name, selected_years, status_ids_list)
            
            # Build result with separate columns for each status
            result = {
                'Property ID': str(prop_id),
                'Property Name': prop_name
            }
            
            # Add column for each selected status
            total = 0
            for status_id in status_ids_list:
                status_name = LEASE_STATUSES[status_id]
                count = status_counts.get(status_name, 0)
                result[status_name] = count
                total += count
                print(f"  ✓ {status_name}: {count}")
            
            result['Total'] = total
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  ✓ Total: {total} leases ({elapsed:.2f} seconds)")
            
            return result
        
        # Process properties in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_prop = {
                executor.submit(process_single_property, prop, idx): (prop, idx) 
                for idx, prop in enumerate(properties, 1)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_prop):
                prop, idx = future_to_prop[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update progress (thread-safe)
                    with progress_lock:
                        completed_count[0] += 1
                        progress_data[task_id]['current'] = completed_count[0]
                        progress_data[task_id]['current_property'] = result['Property Name']
                        progress_data[task_id]['message'] = f"Processing property {completed_count[0]} of {len(properties)}"
                        
                except Exception as e:
                    print(f"  ❌ Error processing {prop.get('MarketingName', 'Unknown')}: {str(e)}")
    
        # Sort by total count descending
        results.sort(key=lambda x: x['Total'], reverse=True)
        
        # Calculate totals
        total_count = sum(r['Total'] for r in results)
        
        total_elapsed = (datetime.now() - report_start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"REPORT COMPLETE")
        print(f"{'='*80}")
        print(f"Total Properties: {len(results)}")
        
        # Print totals by status
        print("\nLeases by Status:")
        for status_id in status_ids_list:
            status_name = LEASE_STATUSES[status_id]
            status_total = sum(r.get(status_name, 0) for r in results)
            print(f"  {status_name}: {status_total}")
        
        print(f"\nTotal Leases (All Selected Statuses): {total_count}")
        print(f"Total Time: {total_elapsed:.2f} seconds ({total_elapsed/60:.1f} minutes)")
        print(f"{'='*80}\n")
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Keep all selected status columns (even if they have 0 leases)
        status_columns_to_keep = [LEASE_STATUSES[status_id] for status_id in status_ids_list]
        
        # Ensure all status columns exist in dataframe (fill with 0 if missing)
        for status_name in status_columns_to_keep:
            if status_name not in df.columns:
                df[status_name] = 0
        
        # Keep all columns: Property ID, Property Name, all selected statuses, Total
        columns_to_keep = ['Property ID', 'Property Name'] + status_columns_to_keep + ['Total']
        df = df[columns_to_keep]
        
        # Recalculate Total based on all selected status columns
        for idx in df.index:
            row_total = sum(df.loc[idx, status_name] for status_name in status_columns_to_keep)
            df.loc[idx, 'Total'] = row_total
        
        # Add totals row with all selected status columns
        totals_row_data = {
            'Property ID': [''],
            'Property Name': ['TOTAL']
        }
        for status_name in status_columns_to_keep:
            totals_row_data[status_name] = [sum(r.get(status_name, 0) for r in results)]
        
        # Calculate total_count from all selected status columns
        total_count = sum(totals_row_data[status_name][0] for status_name in status_columns_to_keep)
        totals_row_data['Total'] = [total_count]
        
        totals_row = pd.DataFrame(totals_row_data)
        df_with_totals = pd.concat([df, totals_row], ignore_index=True)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_with_totals.to_excel(writer, sheet_name='Lease Report', index=False, startrow=1)
            
            # Format the worksheet
            worksheet = writer.sheets['Lease Report']
            
            # Add title row with academic year
            worksheet['B1'] = year_display
            title_cell = worksheet['B1']
            title_cell.font = title_cell.font.copy(bold=True)
            title_cell.alignment = openpyxl.styles.Alignment(horizontal='left', vertical='center')
            
            # Bold headers (now in row 2)
            for cell in worksheet[2]:
                cell.font = cell.font.copy(bold=True)
            
            # Bold totals row
            last_row = len(df_with_totals) + 2  # +2 because of title row
            for cell in worksheet[last_row]:
                cell.font = cell.font.copy(bold=True)
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lease_report_{year_display.replace('-', '_')}_{timestamp}.xlsx"
        
        # Store results for download
        report_results[task_id] = {
            'file': output,
            'filename': filename,
            'total_count': total_count,
            'total_properties': len(results)
        }
        
        # Update progress to complete
        progress_data[task_id]['status'] = 'complete'
        progress_data[task_id]['message'] = 'Report generation complete!'
        progress_data[task_id]['total_count'] = total_count
        progress_data[task_id]['total_properties'] = len(results)
        
    except Exception as e:
        print(f"\n❌ Error processing report: {str(e)}")
        import traceback
        traceback.print_exc()
        progress_data[task_id]['status'] = 'error'
        progress_data[task_id]['message'] = f'Error: {str(e)}'


@app.route('/progress/<task_id>')
def get_progress(task_id):
    """Get progress for a specific task"""
    if task_id not in progress_data:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(progress_data[task_id])


@app.route('/download_report/<task_id>')
def download_report(task_id):
    """Download the completed report"""
    if task_id not in report_results:
        return jsonify({'error': 'Report not found'}), 404
    
    result = report_results[task_id]
    return send_file(
        result['file'],
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=result['filename']
    )

if __name__ == '__main__':
    if not API_KEY:
        print("❌ Error: ENTRATA_API_KEY not found in .env file")
    else:
        app.run(debug=True, port=5000)
