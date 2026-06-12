"""
Test multiple properties to find one with actual lease data
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

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

# Test a variety of properties
test_properties = [
    ("100165016", "1540 Place"),
    ("100148893", "626 on The Park"),
    ("100059195", "800 South"),
    ("771903", "Clemson Edge"),
    ("100059196", "Deep Elm"),
    ("100102568", "Fifteen51"),
    ("100041940", "The Hive"),
    ("100059197", "The Jefferson"),
    ("100142213", "The Nine at Memphis"),
    ("639797", "The Printing House"),
]

print("=" * 80)
print("SEARCHING FOR PROPERTIES WITH LEASE DATA")
print("=" * 80)
print()

properties_with_leases = []

for prop_id, prop_name in test_properties:
    print(f"Testing: {prop_name} (ID: {prop_id})...", end=" ")
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getLeases",
            "version": "r2",
            "params": {
                "propertyId": prop_id
            }
        }
    }
    
    try:
        response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}")
            continue
        
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
        
        if leases and len(leases) > 0:
            print(f"✓ {len(leases)} leases found!")
            properties_with_leases.append((prop_id, prop_name, leases))
        else:
            print("0 leases")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

print()
print("=" * 80)
print("DETAILED RESULTS FOR PROPERTIES WITH LEASES:")
print("=" * 80)

if not properties_with_leases:
    print("\n⚠️  NO PROPERTIES FOUND WITH LEASE DATA")
    print("\nThis could mean:")
    print("  1. Properties are brand new with no leases yet")
    print("  2. Lease data is in a different endpoint")
    print("  3. You might be looking for 'Applications' instead of 'Leases'")
    print("\nSuggestion: Check if Entrata has a 'getApplications' method instead.")
else:
    for prop_id, prop_name, leases in properties_with_leases[:3]:  # Show first 3
        print(f"\n{prop_name} (ID: {prop_id}) - {len(leases)} leases")
        print("-" * 80)
        
        # Analyze statuses
        status_counts = {}
        for lease in leases:
            status = lease.get('LeaseStatus', lease.get('Status', 'Unknown'))
            status_id = lease.get('LeaseStatusTypeId', lease.get('StatusTypeId', '?'))
            key = f"{status} (ID: {status_id})"
            status_counts[key] = status_counts.get(key, 0) + 1
        
        print("Lease Status Breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        print(f"\nSample lease:")
        print(json.dumps(leases[0], indent=2)[:1000])
        print("...")
