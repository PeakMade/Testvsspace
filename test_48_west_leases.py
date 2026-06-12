"""
Test 48 West property which should have 500 pending leases
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

PROPERTY_ID = "1122966"  # 48 West - should have 500 pending leases
PROPERTY_NAME = "48 West"

print("=" * 80)
print(f"TESTING: {PROPERTY_NAME} (ID: {PROPERTY_ID})")
print("Expected: 500 pending leases")
print("=" * 80)
print()

# Test 1: All leases (no filter)
print("Test 1: ALL leases (no status filter)")
print("-" * 80)
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeases",
        "version": "r2",
        "params": {
            "propertyId": PROPERTY_ID
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
        print(f"Result keys: {list(result.keys())}")
        
        # Try to extract leases (lowercase keys for External API)
        leases = []
        if 'leases' in result:
            leases_data = result['leases']
            if isinstance(leases_data, dict):
                leases = leases_data.get('lease', [])
            elif isinstance(leases_data, list):
                leases = leases_data
        elif 'lease' in result:
            leases = result['lease']
        elif 'Leases' in result:
            leases_data = result['Leases']
            if isinstance(leases_data, dict):
                leases = leases_data.get('Lease', [])
        elif 'Lease' in result:
            leases = result['Lease']
        
        if isinstance(leases, dict):
            leases = [leases]
        
        print(f"✓ Got {len(leases)} leases")
        
        if leases:
            print(f"\nFirst lease sample:")
            print(json.dumps(leases[0], indent=2)[:2000])
            
            # Count by status
            status_counts = {}
            for lease in leases:
                status = lease.get('LeaseStatus', lease.get('Status', 'Unknown'))
                status_id = lease.get('LeaseStatusTypeId', lease.get('StatusTypeId', '?'))
                key = f"{status} (StatusID: {status_id})"
                status_counts[key] = status_counts.get(key, 0) + 1
            
            print("\n" + "=" * 80)
            print("LEASE STATUS BREAKDOWN:")
            print("=" * 80)
            for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count}")
        else:
            print("\n⚠️  No lease data returned")
            print("Full response:")
            print(json.dumps(data, indent=2)[:2000])
            
except Exception as e:
    print(f"❌ Exception: {e}")

print()

# Test 2: With status filter "1"
print("Test 2: With leaseStatusTypeIds='1'")
print("-" * 80)
payload['method']['params']['leaseStatusTypeIds'] = "1"
payload['requestId'] = str(int(datetime.now().timestamp() * 1000))

try:
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=60)
    data = response.json()
    
    if 'error' in data.get('response', {}):
        error = data['response']['error']
        print(f"❌ Error {error['code']}: {error['message']}")
    else:
        result = data.get('response', {}).get('result', {})
        leases = []
        if 'leases' in result:
            leases_data = result['leases']
            if isinstance(leases_data, dict):
                leases = leases_data.get('lease', [])
        elif 'lease' in result:
            leases = result['lease']
        elif 'Leases' in result:
            leases_data = result['Leases']
            if isinstance(leases_data, dict):
                leases = leases_data.get('Lease', [])
        elif 'Lease' in result:
            leases = result['Lease']
        
        if isinstance(leases, dict):
            leases = [leases]
        
        print(f"✓ Got {len(leases)} leases with status=1")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print()

# Test 3: Try different status IDs
print("Test 3: Trying various status type IDs...")
print("-" * 80)

for status_id in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getLeases",
            "version": "r2",
            "params": {
                "propertyId": PROPERTY_ID,
                "leaseStatusTypeIds": status_id
            }
        }
    }
    
    try:
        response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        if 'error' not in data.get('response', {}):
            result = data.get('response', {}).get('result', {})
            leases = []
            if 'leases' in result:
                leases_data = result['leases']
                if isinstance(leases_data, dict):
                    leases = leases_data.get('lease', [])
            elif 'lease' in result:
                leases = result['lease']
            elif 'Leases' in result:
                leases_data = result['Leases']
                if isinstance(leases_data, dict):
                    leases = leases_data.get('Lease', [])
            elif 'Lease' in result:
                leases = result['Lease']
            
            if isinstance(leases, dict):
                leases = [leases]
            
            if leases and len(leases) > 0:
                print(f"  Status ID {status_id}: {len(leases)} leases ✓")
        
    except:
        pass
