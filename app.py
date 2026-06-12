"""
Flask Web App for Entrata Lease Reports
Interactive app to select academic years and lease status types
"""
from flask import Flask, render_template, request, jsonify
import os
import requests
import pandas as pd
from datetime import datetime, timedelta, date as date_type
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
PROPERTIES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

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

_ENTRATA_CAP = 500  # Entrata's hard per-request record limit


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


def _query_ids_in_range(headers, property_id, date_from, date_to, status_ids):
    """Query lease IDs for a property within a moveInDate range.
    Returns a list of ID strings, or None on API error."""
    params = {
        "propertyId": str(property_id),
        "leaseStatusTypeIds": status_ids,  # Now accepts multiple statuses
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
    whenever the API returns exactly 500 records (the hard cap)."""
    
    ids = _query_ids_in_range(headers, property_id, date_from, date_to, status_ids)
    if ids is None:
        return set()
    
    if len(ids) < _ENTRATA_CAP:
        return set(ids)
    
    if date_from >= date_to:
        return set(ids)
    
    mid = date_from + (date_to - date_from) // 2
    left  = _collect_all_ids(headers, property_id, date_from, mid, status_ids, depth + 1)
    right = _collect_all_ids(headers, property_id, mid + timedelta(days=1), date_to, status_ids, depth + 1)
    combined = left | right
    return combined


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
        
        year_ids = _collect_all_ids(
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
    """Run the report with selected parameters"""
    data = request.get_json()
    selected_year = data.get('year')
    selected_statuses = data.get('statuses', [])
    
    if not selected_year or not selected_statuses:
        return jsonify({'error': 'Please select a year and at least one status'}), 400
    
    selected_years = [int(selected_year)]
    
    # Convert status IDs to comma-separated string
    status_ids = ','.join(selected_statuses)
    status_names = ', '.join([LEASE_STATUSES[s] for s in selected_statuses])
    year_display = f"{selected_years[0]}-{selected_years[0] + 1}"
    
    # Get all properties
    properties = get_all_properties()
    
    if not properties:
        return jsonify({'error': 'Could not retrieve properties'}), 500
    
    results = []
    
    for prop in properties:
        prop_id = prop.get('PropertyID')
        prop_name = prop.get('MarketingName', f"Property {prop_id}")
        
        count = get_leases_for_property(prop_id, prop_name, selected_years, status_ids)
        
        results.append({
            'property_id': str(prop_id),
            'property_name': prop_name,
            'count': count
        })
    
    # Sort by count descending
    results.sort(key=lambda x: x['count'], reverse=True)
    
    # Calculate summary
    total_count = sum(r['count'] for r in results)
    avg_count = total_count / len(results) if results else 0
    properties_with_leases = sum(1 for r in results if r['count'] > 0)
    
    return jsonify({
        'success': True,
        'results': results,
        'summary': {
            'total_properties': len(results),
            'total_count': total_count,
            'avg_count': round(avg_count, 1),
            'properties_with_leases': properties_with_leases,
            'selected_year': year_display,
            'selected_statuses': status_names
        }
    })


if __name__ == '__main__':
    if not API_KEY:
        print("❌ Error: ENTRATA_API_KEY not found in .env file")
    else:
        app.run(debug=True, port=5000)
