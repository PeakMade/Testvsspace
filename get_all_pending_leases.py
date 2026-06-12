"""
Get Pending Leases Across Portfolio - Using Entrata API
Queries Entrata API for all properties and returns pending lease counts
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta, date as date_type
from dotenv import load_dotenv
import json
import time
import glob

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
PROPERTIES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

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
            error = data['response']['error']
            print(f"❌ API Error {error['code']}: {error['message']}")
            return []
        
        # Extract properties from response
        result = data.get('response', {}).get('result', {})
        physical_property = result.get('PhysicalProperty', {})
        properties = physical_property.get('Property', [])
        
        # Ensure it's a list
        if isinstance(properties, dict):
            properties = [properties]
        
        # Save full response for reference
        with open('properties.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        # Filter to only active residential properties (excluding Canadian)
        filtered_properties = []
        exclude_keywords = ['retail', 'reit', 'llc', 'corporate', 'shuttle', 'condominium', 'assoc', 'master', 'ucc', 'university center', 'gateway']
        exclude_countries = ['CAN']  # Exclude Canadian properties (using 3-letter code to avoid confusion with CA state)
        
        for prop in properties:
            prop_name = prop.get('MarketingName', '')
            is_disabled = prop.get('IsDisabled', 0)
            
            # Skip if disabled (archived)
            if is_disabled == 1:
                continue
            
            # Skip if name starts with 'z' or 'Z'
            if prop_name.startswith('z') or prop_name.startswith('Z'):
                continue
            
            # Skip if name contains excluded keywords
            if any(keyword in prop_name.lower() for keyword in exclude_keywords):
                continue
            
            # Skip Canadian properties
            address = prop.get('Address', {})
            country = address.get('Country', '')
            if country in exclude_countries:
                print(f"  Excluding {prop_name} (Country: {country})")
                continue
            
            filtered_properties.append(prop)
        
        print(f"  Filtered from {len(properties)} total to {len(filtered_properties)} active residential properties (excluding Canada)")
        
        return filtered_properties
        
    except Exception as e:
        print(f"❌ Exception getting properties: {e}")
        return []

_ENTRATA_CAP = 500  # Entrata's hard per-request record limit


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


def _query_ids_in_range(headers, property_id, date_from, date_to):
    """Query pending lease IDs for a property within a moveInDate range.
    Returns a list of ID strings, or None on API error."""
    params = {
        "propertyId": str(property_id),
        "leaseStatusTypeIds": "125",
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


def _collect_all_ids(headers, property_id, date_from, date_to, depth=0):
    """Recursively collect all unique pending lease IDs, bisecting the date range
    whenever the API returns exactly 500 records (the hard cap).
    Continues splitting until every sub-range is below the cap."""
    
    ids = _query_ids_in_range(headers, property_id, date_from, date_to)
    if ids is None:
        return set()
    
    if len(ids) < _ENTRATA_CAP:
        # Under the cap — we have all records in this range
        return set(ids)
    
    # Hit the cap! Log warning and bisect
    print(f"  ⚠️  Hit 500-record cap for range {date_from} to {date_to} - bisecting...")
    
    if date_from >= date_to:
        # Single day still hitting the cap — extremely unlikely but log it
        print(f"  ⚠️  Warning: single-day range {date_from} still at cap for property {property_id}")
        return set(ids)
    # Hit the cap; bisect and take the union of both halves
    mid = date_from + (date_to - date_from) // 2
    left  = _collect_all_ids(headers, property_id, date_from, mid, depth + 1)
    right = _collect_all_ids(headers, property_id, mid + timedelta(days=1), date_to, depth + 1)
    combined = left | right
    return combined


def get_pending_leases_for_property(property_id, property_name):
    """Get count of pending leases, using recursive date-range bisection to
    bypass Entrata's hard 500-record-per-request cap. No upper limit on results."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    try:
        # Query for current academic year (August to July)
        today = date_type.today()
        current_year = today.year
        current_month = today.month
        
        # Determine academic year: if we're before August, use current year; otherwise next year
        if current_month >= 8:  # August or later
            academic_year_start = current_year
        else:  # Before August
            academic_year_start = current_year
        
        start_date = date_type(academic_year_start, 8, 1)  # August 1
        end_date = date_type(academic_year_start + 1, 7, 31)  # July 31 next year
        
        all_ids = _collect_all_ids(
            headers, property_id,
            start_date,
            end_date
        )
        total = len(all_ids)
        print(f"  ✅ Final count for academic year {academic_year_start}-{academic_year_start + 1}: {total} unique pending leases")
        return total
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return -1

def load_properties_from_csv(csv_file):
    """Load property IDs and names from CSV file"""
    try:
        df = pd.read_csv(csv_file)
        
        # Try to find property ID and name columns (case-insensitive)
        id_col = None
        name_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'property' in col_lower and 'id' in col_lower:
                id_col = col
            elif 'property' in col_lower and 'name' in col_lower:
                name_col = col
            elif col_lower == 'propertyid':
                id_col = col
            elif col_lower == 'propertyname':
                name_col = col
        
        if not id_col:
            print("❌ Could not find Property ID column in CSV")
            print(f"Available columns: {', '.join(df.columns)}")
            return []
        
        properties = []
        for idx, row in df.iterrows():
            prop_id = row[id_col]
            prop_name = row[name_col] if name_col else f"Property {prop_id}"
            properties.append({'id': prop_id, 'name': prop_name})
        
        return properties
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return []

def cleanup_old_reports(pattern: str, keep_count: int = 1):
    """Delete old report files, keeping only the most recent ones.
    
    Args:
        pattern: File pattern to match (e.g., 'pending_leases_report_*.xlsx')
        keep_count: Number of most recent files to keep (default: 1)
    """
    files = glob.glob(pattern)
    if len(files) <= keep_count:
        return
    
    # Sort by modification time, newest first
    files_with_time = [(f, os.path.getmtime(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # Delete old files
    files_to_delete = [f[0] for f in files_with_time[keep_count:]]
    if files_to_delete:
        print(f"\n🗑️  Cleaning up {len(files_to_delete)} old report(s)...")
        for file in files_to_delete:
            try:
                os.remove(file)
                print(f"  Deleted: {os.path.basename(file)}")
            except Exception as e:
                print(f"  ⚠️  Could not delete {os.path.basename(file)}: {e}")

def main():
    print("=" * 80)
    print("ENTRATA PENDING LEASES REPORT - ALL PROPERTIES")
    print("=" * 80)
    print()
    
    if not API_KEY:
        print("❌ Error: ENTRATA_API_KEY not found in .env file")
        return
    
    # Get all properties from API
    print("Fetching all properties from Entrata API...")
    api_properties = get_all_properties()
    
    properties = []
    
    if api_properties:
        print(f"✓ Retrieved {len(api_properties)} properties from API")
        for prop in api_properties:
            properties.append({
                'id': prop.get('PropertyID'),
                'name': prop.get('MarketingName', prop.get('PropertyLookupCode', f"Property {prop.get('PropertyID')}"))
            })
    else:
        print("⚠️  No properties returned from API. Falling back to manual entry...")
        
        # Option 1: Load from CSV file
        print("\nLooking for property list CSV file...")
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'propert' in f.lower()]
        
        if csv_files:
            print(f"Found: {', '.join(csv_files)}")
            csv_file = csv_files[0]
            print(f"Loading properties from: {csv_file}")
            properties = load_properties_from_csv(csv_file)
        
        # Option 2: Manual property ID entry
        if not properties:
            print("\nNo property CSV found. Please enter property IDs manually.")
            print("Enter property IDs (one per line, or comma-separated).")
            print("Press Enter twice when done:\n")
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            # Parse property IDs
            for line in lines:
                ids = [x.strip() for x in line.replace(',', ' ').split()]
                for pid in ids:
                    if pid.isdigit():
                        properties.append({'id': pid, 'name': f'Property {pid}'})
    
    if not properties:
        print("\n❌ No properties to query. Exiting.")
        return
    
    print(f"\n✓ Processing {len(properties)} properties")
    print("\n" + "=" * 80)
    print("Querying Entrata API for pending leases...")
    print("=" * 80)
    
    results = []
    errors = []
    
    for idx, prop in enumerate(properties, 1):
        prop_id = prop['id']
        prop_name = prop['name']
        
        print(f"\n[{idx}/{len(properties)}] {prop_name} (ID: {prop_id})")
        
        count = get_pending_leases_for_property(prop_id, prop_name)
        
        if count >= 0:
            print(f"  ✓ {count} pending lease(s)")
            results.append({
                'Property ID': str(prop_id),
                'Property Name': prop_name,
                'Pending Lease Count': count
            })
        else:
            print(f"  ❌ Error querying property")
            errors.append(f"{prop_name} (ID: {prop_id})")
            results.append({
                'Property ID': str(prop_id),
                'Property Name': prop_name,
                'Pending Lease Count': -1
            })
        
        # Rate limiting
        time.sleep(0.25)
    
    # Create DataFrame
    df = pd.DataFrame(results)
    df_valid = df[df['Pending Lease Count'] >= 0].copy()
    df_errors = df[df['Pending Lease Count'] < 0].copy()
    
    # Sort by pending count (ascending - lowest to highest)
    df_valid = df_valid.sort_values('Pending Lease Count', ascending=True)
    
    # Display results
    print("\n" + "=" * 80)
    print("RESULTS - PENDING LEASE COUNTS BY PROPERTY")
    print("=" * 80)
    print(df_valid.to_string(index=False))
    
    if not df_errors.empty:
        print("\n" + "=" * 80)
        print(f"⚠️  PROPERTIES WITH ERRORS ({len(df_errors)}):")
        print("=" * 80)
        for error in errors:
            print(f"  - {error}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Properties Queried: {len(properties)}")
    print(f"Successful Queries: {len(df_valid)}")
    if not df_errors.empty:
        print(f"Failed Queries: {len(df_errors)}")
    print(f"\nTotal Pending Leases: {df_valid['Pending Lease Count'].sum()}")
    print(f"Average per Property: {df_valid['Pending Lease Count'].mean():.1f}")
    print(f"Properties with Pending Leases: {(df_valid['Pending Lease Count'] > 0).sum()}")
    print(f"Max Pending (Single Property): {df_valid['Pending Lease Count'].max()}")
    
    # Export to Excel with TOTAL row
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"pending_leases_report_{timestamp}.xlsx"
    csv_file = f"pending_leases_report_{timestamp}.csv"
    
    # Clean up old reports before saving new ones
    cleanup_old_reports("pending_leases_report_*.xlsx", keep_count=1)
    cleanup_old_reports("pending_leases_report_*.csv", keep_count=1)
    
    # Add totals row
    totals_row = pd.DataFrame({
        'Property ID': [''],
        'Property Name': ['TOTAL'],
        'Pending Lease Count': [df_valid['Pending Lease Count'].sum()]
    })
    df_with_totals = pd.concat([df_valid, totals_row], ignore_index=True)
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df_with_totals.to_excel(writer, sheet_name='Pending Leases', index=False)
        
        # Format totals row (bold)
        worksheet = writer.sheets['Pending Leases']
        last_row = len(df_with_totals) + 1
        for cell in worksheet[last_row]:
            cell.font = cell.font.copy(bold=True)
        
        # Add errors sheet if any
        if not df_errors.empty:
            df_errors.to_excel(writer, sheet_name='Errors', index=False)
    
    print(f"\n✓ Report exported to: {excel_file}")
    
    # Also save CSV
    df_with_totals.to_csv(csv_file, index=False)
    print(f"✓ Report exported to: {csv_file}")

if __name__ == "__main__":
    main()
