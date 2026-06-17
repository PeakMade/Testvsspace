"""
Comprehensive test of ALL possible pagination parameter formats for Entrata API
"""
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

PROPERTY_ID = "1122966"   # 48 West - has >500 pending leases

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

def extract_leases(result):
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

def test_pagination_format(format_name, params_page1, params_page2):
    """Test a specific pagination parameter format"""
    print(f"\n{'='*80}")
    print(f"Testing: {format_name}")
    print(f"{'='*80}")
    
    # Page 1
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getLeases",
            "version": "r2",
            "params": params_page1
        }
    }
    
    print(f"Page 1 params: {json.dumps(params_page1, indent=2)}")
    resp1 = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
    data1 = resp1.json()
    
    if 'error' in data1.get('response', {}):
        err = data1['response']['error']
        print(f"❌ Page 1 Error: {err}")
        return False
    
    result1 = data1.get('response', {}).get('result', {})
    leases1 = extract_leases(result1)
    ids1 = [l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in leases1]
    print(f"Page 1: {len(leases1)} leases, first 3 IDs: {ids1[:3]}")
    
    # Page 2
    payload['method']['params'] = params_page2
    payload['requestId'] = str(int(datetime.now().timestamp() * 1000))
    
    print(f"Page 2 params: {json.dumps(params_page2, indent=2)}")
    resp2 = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
    data2 = resp2.json()
    
    if 'error' in data2.get('response', {}):
        err = data2['response']['error']
        print(f"❌ Page 2 Error: {err}")
        return False
    
    result2 = data2.get('response', {}).get('result', {})
    leases2 = extract_leases(result2)
    ids2 = [l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in leases2]
    print(f"Page 2: {len(leases2)} leases, first 3 IDs: {ids2[:3]}")
    
    # Compare
    if len(leases2) == 0:
        print("⚠️  Page 2 returned 0 records - can't tell if pagination works")
        return False
    
    set1 = set(ids1)
    set2 = set(ids2)
    overlap = set1 & set2
    
    if overlap == set1 or set2 == set1:
        print("❌ SAME records - pagination NOT working")
        return False
    elif len(overlap) == 0:
        print("✅ DIFFERENT records - pagination WORKS!")
        return True
    else:
        print(f"⚠️  Partial overlap ({len(overlap)} IDs) - unreliable")
        return False

# Base params
base_params = {
    "propertyId": PROPERTY_ID,
    "leaseStatusTypeIds": "1"
}

print("="*80)
print("COMPREHENSIVE PAGINATION TEST")
print("="*80)

results = {}

# Test 1: Nested paging object
params1 = {**base_params, "paging": {"page": 1, "perPage": 500}}
params2 = {**base_params, "paging": {"page": 2, "perPage": 500}}
results["Nested paging {page, perPage}"] = test_pagination_format(
    "Nested paging {page, perPage}", params1, params2
)

# Test 2: Top-level page_no, per_page
params1 = {**base_params, "page_no": 1, "per_page": 500}
params2 = {**base_params, "page_no": 2, "per_page": 500}
results["Top-level page_no, per_page"] = test_pagination_format(
    "Top-level page_no, per_page", params1, params2
)

# Test 3: Top-level page, perPage
params1 = {**base_params, "page": 1, "perPage": 500}
params2 = {**base_params, "page": 2, "perPage": 500}
results["Top-level page, perPage"] = test_pagination_format(
    "Top-level page, perPage", params1, params2
)

# Test 4: offset, limit
params1 = {**base_params, "offset": 0, "limit": 500}
params2 = {**base_params, "offset": 500, "limit": 500}
results["offset, limit"] = test_pagination_format(
    "offset, limit", params1, params2
)

# Test 5: skip, take
params1 = {**base_params, "skip": 0, "take": 500}
params2 = {**base_params, "skip": 500, "take": 500}
results["skip, take"] = test_pagination_format(
    "skip, take", params1, params2
)

# Test 6: pageNumber, pageSize
params1 = {**base_params, "pageNumber": 1, "pageSize": 500}
params2 = {**base_params, "pageNumber": 2, "pageSize": 500}
results["pageNumber, pageSize"] = test_pagination_format(
    "pageNumber, pageSize", params1, params2
)

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
for format_name, worked in results.items():
    status = "✅ WORKS" if worked else "❌ DOESN'T WORK"
    print(f"{status:20} - {format_name}")

if not any(results.values()):
    print("\n⚠️  NO PAGINATION METHOD WORKS - must use date-range bisection")
else:
    print("\n✅ At least one pagination method works!")
print("="*80)
