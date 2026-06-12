"""
Test different lease status types to find the correct one for pending leases
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

# Test with a property that likely has leases
TEST_PROPERTY_ID = "100165016"  # 1540 Place

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

print("=" * 80)
print("TESTING LEASE STATUS TYPES")
print("=" * 80)
print(f"Test Property: 1540 Place (ID: {TEST_PROPERTY_ID})")
print()

# Test 1: Get ALL leases (no status filter)
print("Test 1: Getting ALL leases (no status filter)")
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
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
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
            print("\nSample lease data (first lease):")
            print(json.dumps(leases[0], indent=2)[:1500])
            
            # Count by status
            status_counts = {}
            for lease in leases:
                status = lease.get('LeaseStatus', 'Unknown')
                status_id = lease.get('LeaseStatusTypeId', 'Unknown')
                key = f"{status} (ID: {status_id})"
                status_counts[key] = status_counts.get(key, 0) + 1
            
            print("\n" + "=" * 80)
            print("LEASE STATUS BREAKDOWN:")
            print("=" * 80)
            for status, count in sorted(status_counts.items()):
                print(f"  {status}: {count} leases")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print()

# Test 2: Try status "1" specifically
print("Test 2: Querying with leaseStatusTypeIds='1' (your current filter)")
print("-" * 80)
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeases",
        "version": "r2",
        "params": {
            "propertyId": TEST_PROPERTY_ID,
            "leaseStatusTypeIds": "1"
        }
    }
}

try:
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
    data = response.json()
    
    if 'error' in data.get('response', {}):
        error = data['response']['error']
        print(f"❌ Error {error['code']}: {error['message']}")
    else:
        result = data.get('response', {}).get('result', {})
        leases = []
        if 'Leases' in result:
            leases_data = result['Leases']
            if isinstance(leases_data, dict):
                leases = leases_data.get('Lease', [])
        elif 'Lease' in result:
            leases = result['Lease']
        
        if isinstance(leases, dict):
            leases = [leases]
        
        print(f"✓ Found {len(leases)} leases with status type ID = 1")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print()
print("=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("Look at the 'LEASE STATUS BREAKDOWN' above to identify which status")
print("represents 'Pending' or 'Application Submitted' leases in your system.")
print()
print("Common lease status types:")
print("  - Pending / Application")
print("  - Current / Active")
print("  - Future / Approved")
print("  - Notice / Move Out")
print("  - Past / Cancelled")
