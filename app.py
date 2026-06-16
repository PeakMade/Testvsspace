"""
Flask Web App for Entrata Lease Reports
Interactive app to select academic years and lease status types
"""
from flask import Flask, render_template, request, jsonify, send_file, Response
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

# Note: Entrata API supports pagination via page_no/per_page parameters
# No longer need bisection workaround


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
        exclude_keywords = ['retail', 'reit', 'llc', 'corporate', 'shuttle', 'condominium', 'assoc', 'master', 'ucc', 'university center', 'gateway']
        exclude_countries = ['CAN']
        
        for prop in properties:
            prop_name = prop.get('MarketingName', '')
            is_disabled = prop.get('IsDisabled', 0)
            
            if is_disabled == 1:
                continue
            
            if prop_name.startswith('z') or prop_name.startswith('Z'):
                continue
            
            if any(keyword in prop_name.lower() for keyword in exclude_keywords):
                continue
            
            address = prop.get('Address', {})
            country = address.get('Country', '')
            if country in exclude_countries:
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


def _query_all_leases_paginated(headers, property_id, date_from, date_to, status_ids):
    """Query all lease IDs for a property using native API pagination.
    Returns a set of unique ID strings."""
    all_ids = set()
    page_no = 1
    per_page = 500
    
    while True:
        params = {
            "propertyId": str(property_id),
            "leaseStatusTypeIds": status_ids,
            "moveInDateFrom": date_from.strftime("%m/%d/%Y"),
            "moveInDateTo": date_to.strftime("%m/%d/%Y"),
            "page_no": page_no,
            "per_page": per_page
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
                print(f"    ⚠️  API error on page {page_no}")
                break
            
            result = data.get('response', {}).get('result', {})
            leases = _extract_leases_from_result(result)
            
            if not leases or len(leases) == 0:
                # No more leases
                break
            
            # Extract IDs and add to set
            page_ids = [str(l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') or '') 
                       for l in leases if (l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id'))]
            all_ids.update(page_ids)
            
            # If we got fewer than per_page, we've reached the end
            if len(leases) < per_page:
                break
            
            # Move to next page
            page_no += 1
            
            # Safety check
            if page_no > 100:
                print(f"    ⚠️  Safety limit: stopped after 100 pages")
                break
                
        except Exception as e:
            print(f"    ⚠️  Exception on page {page_no}: {e}")
            break
    
    return all_ids


def get_leases_for_property(property_id, property_name, academic_years, status_ids):
    """Get count of leases for specified academic years and statuses."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    
    total_ids = set()
    
    for year in academic_years:
        start_date = date_type(year, 8, 1)  # August 1
        end_date = date_type(year + 1, 7, 31)  # July 31 next year
        
        year_ids = _query_all_leases_paginated(
            headers, property_id,
            start_date,
            end_date,
            status_ids
        )
        total_ids.update(year_ids)
    
    return len(total_ids)


@app.route('/')
def index():
    """Main page with form"""
    # Generate list of academic years (current +/- 5 years)
    today = date_type.today()
    current_year = today.year if today.month < 8 else today.year
    
    years = list(range(current_year - 2, current_year + 6))
    
    return render_template('index.html', 
                         years=years, 
                         statuses=LEASE_STATUSES,
                         current_year=current_year)


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
        
        # Convert status IDs to comma-separated string
        status_ids = ','.join(selected_statuses)
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
            
            count = get_leases_for_property(prop_id, prop_name, selected_years, status_ids)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  ✓ Found {count} leases ({elapsed:.2f} seconds)")
            
            return {
                'Property ID': str(prop_id),
                'Property Name': prop_name,
                'Lease Count': count
            }
        
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
    
        # Sort by count descending
        results.sort(key=lambda x: x['Lease Count'], reverse=True)
        
        # Calculate total
        total_count = sum(r['Lease Count'] for r in results)
        
        total_elapsed = (datetime.now() - report_start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"REPORT COMPLETE")
        print(f"{'='*80}")
        print(f"Total Properties: {len(results)}")
        print(f"Total Leases: {total_count}")
        print(f"Total Time: {total_elapsed:.2f} seconds ({total_elapsed/60:.1f} minutes)")
        print(f"{'='*80}\n")
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Add totals row
        totals_row = pd.DataFrame({
            'Property ID': [''],
            'Property Name': ['TOTAL'],
            'Lease Count': [total_count]
        })
        df_with_totals = pd.concat([df, totals_row], ignore_index=True)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_with_totals.to_excel(writer, sheet_name='Lease Report', index=False)
            
            # Format the worksheet
            worksheet = writer.sheets['Lease Report']
            
            # Bold headers
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
            
            # Bold totals row
            last_row = len(df_with_totals) + 1
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
