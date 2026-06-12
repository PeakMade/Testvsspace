"""
Diagnostic test to figure out why Peak Campus shows different numbers
Testing different date fields, status combinations, and date ranges
"""
import os
import requests
import json
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

# 48 West - Peak Campus shows 920 and 714, we found 197
PROPERTY_ID = "1122966"
PROPERTY_NAME = "48 WEST"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

print("=" * 80)
print(f"DIAGNOSTIC TEST: {PROPERTY_NAME}")
print("=" * 80)
print(f"Peak Campus shows: ~920 and ~714")
print(f"Our script found: 197 pending leases (status=1, move-in dates 8/1/2026-7/31/2027)")
print()

# Test different scenarios
tests = [
    {
        "name": "Test 1: Status=1, Move-in dates 2026-2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "moveInDateFrom": "08/01/2026",
            "moveInDateTo": "07/31/2027"
        }
    },
    {
        "name": "Test 2: ALL statuses, Move-in dates 2026-2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "moveInDateFrom": "08/01/2026",
            "moveInDateTo": "07/31/2027"
        }
    },
    {
        "name": "Test 3: Status=1, Application dates 2026-2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "applicationDateFrom": "08/01/2026",
            "applicationDateTo": "07/31/2027"
        }
    },
    {
        "name": "Test 4: Status=1, Lease Start dates 2026-2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "leaseStartDateFrom": "08/01/2026",
            "leaseStartDateTo": "07/31/2027"
        }
    },
    {
        "name": "Test 5: Status=1, Move-in ENTIRE 2026",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "moveInDateFrom": "01/01/2026",
            "moveInDateTo": "12/31/2026"
        }
    },
    {
        "name": "Test 6: Status=1, Move-in ENTIRE 2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "moveInDateFrom": "01/01/2027",
            "moveInDateTo": "12/31/2027"
        }
    },
    {
        "name": "Test 7: Status=1, NO date filter",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1"
        }
    },
    {
        "name": "Test 8: ALL statuses, NO date filter",
        "params": {
            "propertyId": PROPERTY_ID
        }
    },
    {
        "name": "Test 9: Multiple statuses (1,2,3), Move-in 2026-2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1,2,3",
            "moveInDateFrom": "08/01/2026",
            "moveInDateTo": "07/31/2027"
        }
    },
    {
        "name": "Test 10: Multiple statuses (1,2,3,4,5), Move-in 2026-2027",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1,2,3,4,5",
            "moveInDateFrom": "08/01/2026",
            "moveInDateTo": "07/31/2027"
        }
    },
]

for test in tests:
    print("=" * 80)
    print(test["name"])
    print("-" * 80)
    print(f"Parameters: {json.dumps(test['params'], indent=2)}")
    print()
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getLeases",
            "version": "r2",
            "params": test["params"]
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
                ld = result['Leases']
                leases = ld.get('Lease', []) if isinstance(ld, dict) else ld
            elif 'leases' in result:
                ld = result['leases']
                leases = ld.get('lease', []) if isinstance(ld, dict) else ld
            elif 'Lease' in result:
                leases = result['Lease']
            elif 'lease' in result:
                leases = result['lease']
            
            if isinstance(leases, dict):
                leases = [leases]
            
            count = len(leases)
            print(f"✓ Found {count} leases")
            
            # If we found some leases, show sample data
            if leases and count > 0:
                # Count by status
                status_counts = {}
                for lease in leases:
                    status = lease.get('LeaseStatus', lease.get('Status', 'Unknown'))
                    status_id = lease.get('LeaseStatusTypeId', lease.get('StatusId', 'Unknown'))
                    key = f"{status} (ID: {status_id})"
                    status_counts[key] = status_counts.get(key, 0) + 1
                
                print(f"\nStatus breakdown:")
                for status, cnt in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {status}: {cnt}")
                
                # Show sample lease
                if count <= 3:
                    print(f"\nSample lease:")
                    print(json.dumps(leases[0], indent=2)[:1500])
            
            # HIGHLIGHT if this matches Peak Campus numbers
            if count >= 700 and count <= 750:
                print(f"\n🎯 THIS MIGHT BE IT! Count={count} is close to Peak Campus number (714)")
            elif count >= 900 and count <= 950:
                print(f"\n🎯 THIS MIGHT BE IT! Count={count} is close to Peak Campus number (920)")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
    
    print()

print("=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("Look for the test that returns ~714 or ~920 leases to match Peak Campus.")
print("That will tell us which combination of status + date field is correct.")
