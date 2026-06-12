"""
Check lease status types for 48 WEST property
"""
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

# 48 West property
TEST_PROPERTY_ID = "1122966"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

print("=" * 80)
print("48 WEST - LEASE STATUS ANALYSIS")
print("=" * 80)
print(f"Property ID: {TEST_PROPERTY_ID}")
print()

# Get ALL leases (no status filter)
print("Fetching ALL leases (no status filter)...")
print("-" * 80)
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeases",
        "version": "r2",
        "params": {
            "propertyId": TEST_PROPERTY_ID
        }
    }
}

try:
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=60)
    data = response.json()
    
    if 'error' in data.get('response', {}):
        error = data['response']['error']
        print(f"❌ Error {error['code']}: {error['message']}")
    else:
        result = data.get('response', {}).get('result', {})
        
        # Extract leases
        leases = []
        if 'Leases' in result:
            leases_data = result['Leases']
            if isinstance(leases_data, dict):
                leases = leases_data.get('Lease', [])
            elif isinstance(leases_data, list):
                leases = leases_data
        elif 'Lease' in result:
            leases = result['Lease']
        
        if isinstance(leases, dict):
            leases = [leases]
        
        print(f"✓ Found {len(leases)} total leases")
        
        if leases:
            # Show sample lease structure
            print("\n" + "=" * 80)
            print("SAMPLE LEASE STRUCTURE (first lease):")
            print("=" * 80)
            sample = leases[0]
            print(json.dumps(sample, indent=2)[:2000])
            
            # Count by status
            status_counts = {}
            status_id_counts = {}
            
            for lease in leases:
                # Get status name
                status = lease.get('LeaseStatus', lease.get('Status', 'Unknown'))
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Get status ID
                status_id = lease.get('LeaseStatusTypeId', lease.get('StatusId', 'Unknown'))
                status_id_counts[status_id] = status_id_counts.get(status_id, 0) + 1
            
            print("\n" + "=" * 80)
            print("LEASE STATUS BREAKDOWN (by name):")
            print("=" * 80)
            for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count} leases")
            
            print("\n" + "=" * 80)
            print("LEASE STATUS BREAKDOWN (by ID):")
            print("=" * 80)
            for status_id, count in sorted(status_id_counts.items(), key=lambda x: str(x[0])):
                print(f"  Status ID {status_id}: {count} leases")
            
            # Check lease dates for 2026-2027
            print("\n" + "=" * 80)
            print("DATE ANALYSIS FOR 2026-2027 ACADEMIC YEAR:")
            print("=" * 80)
            
            from datetime import date
            start_2026 = date(2026, 8, 1)
            end_2027 = date(2027, 7, 31)
            
            academic_year_count = 0
            for lease in leases:
                # Try different date field names
                start_date_str = lease.get('StartDate', lease.get('LeaseStartDate', ''))
                if start_date_str:
                    try:
                        # Parse date (format might be YYYY-MM-DD or MM/DD/YYYY)
                        if '-' in start_date_str:
                            start_date = date.fromisoformat(start_date_str.split('T')[0])
                        elif '/' in start_date_str:
                            parts = start_date_str.split('/')
                            start_date = date(int(parts[2]), int(parts[0]), int(parts[1]))
                        else:
                            continue
                        
                        if start_2026 <= start_date <= end_2027:
                            academic_year_count += 1
                    except:
                        pass
            
            print(f"Leases with start dates in 2026-2027 academic year: {academic_year_count}")
            print(f"Total leases returned: {len(leases)}")
        else:
            print("No leases found.")
        
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("WHAT THIS MEANS:")
print("=" * 80)
print("If you see many more leases here than in your report (197), then we need")
print("to either:")
print("  1. Include additional lease status IDs beyond just '1'")
print("  2. Check if Peak Campus is looking at a different data source")
print("  3. Verify the date filtering logic")
