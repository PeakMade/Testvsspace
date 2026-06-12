"""
Test whether the Entrata getLeases API supports pagination or has a hard 500-record cap.
Runs against a known large property (48 West, which returned exactly 500 in previous runs).
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

PROPERTY_ID = "1122966"   # 48 West - previously capped at 500
PROPERTY_NAME = "48 West"

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

print("=" * 80)
print(f"PAGINATION TEST  —  {PROPERTY_NAME} (ID: {PROPERTY_ID})")
print("=" * 80)

# ── Test 1: page 1 ────────────────────────────────────────────────────────────
print("\nTest 1: page=1, perPage=500")
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeases",
        "version": "r2",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "paging": {"page": 1, "perPage": 500}
        }
    }
}
resp = requests.post(LEASES_URL, headers=headers, json=payload, timeout=60)
data = resp.json()

page1_leases = []
total_count_from_meta = None

if 'error' in data.get('response', {}):
    err = data['response']['error']
    print(f"❌ Error {err['code']}: {err['message']}")
else:
    response_body = data.get('response', {})
    result = response_body.get('result', {})

    # Look for totalCount / totalRecords in any part of the response
    for key in ('totalCount', 'totalRecords', 'total', 'TotalCount', 'TotalRecords'):
        val = response_body.get(key) or result.get(key)
        if val is not None:
            total_count_from_meta = val
            print(f"  ✓ Metadata '{key}' = {val}")
            break

    page1_leases = extract_leases(result)
    first_ids = [l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in page1_leases[:5]]
    print(f"  Page 1 returned: {len(page1_leases)} leases")
    print(f"  First 5 lease IDs: {first_ids}")
    print(f"  Full response keys: {list(response_body.keys())}")
    print(f"  Result keys: {list(result.keys())}")

# ── Test 2: page 2 ────────────────────────────────────────────────────────────
print("\nTest 2: page=2, perPage=500")
payload['method']['params']['paging'] = {"page": 2, "perPage": 500}
payload['requestId'] = str(int(datetime.now().timestamp() * 1000))

resp2 = requests.post(LEASES_URL, headers=headers, json=payload, timeout=60)
data2 = resp2.json()

if 'error' in data2.get('response', {}):
    err = data2['response']['error']
    print(f"❌ Error {err['code']}: {err['message']}")
else:
    result2 = data2.get('response', {}).get('result', {})
    page2_leases = extract_leases(result2)
    second_ids = [l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in page2_leases[:5]]
    print(f"  Page 2 returned: {len(page2_leases)} leases")
    print(f"  First 5 lease IDs: {second_ids}")

    if page1_leases and page2_leases:
        p1_ids = set(l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in page1_leases)
        p2_ids = set(l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in page2_leases)
        overlap = p1_ids & p2_ids

        print(f"\n{'='*80}")
        if overlap == p1_ids or p2_ids == p1_ids:
            print("⚠️  SAME records on page 2 — API is ignoring the paging param (hard 500 cap).")
            print("    Will need date-range splitting to work around this.")
        elif len(page2_leases) == 0:
            print("⚠️  Page 2 returned 0 records — either only 500 exist, or paging not supported.")
        elif len(overlap) == 0:
            print("✅ PAGINATION WORKS — page 2 returned different records!")
            print(f"    Total across 2 pages: {len(page1_leases) + len(page2_leases)}")
        else:
            print(f"⚠️  Partial overlap ({len(overlap)} shared IDs) — paging may be unreliable.")
    else:
        print("  (Could not compare pages — one returned empty)")

# ── Test 3: try alternate paging param names ──────────────────────────────────
print("\nTest 3: Trying alternate pagination param names (page_number / per_page)")
payload3 = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeases",
        "version": "r2",
        "params": {
            "propertyId": PROPERTY_ID,
            "leaseStatusTypeIds": "1",
            "page_number": 2,
            "per_page": 500
        }
    }
}
resp3 = requests.post(LEASES_URL, headers=headers, json=payload3, timeout=60)
data3 = resp3.json()
if 'error' not in data3.get('response', {}):
    result3 = data3.get('response', {}).get('result', {})
    alt_leases = extract_leases(result3)
    alt_ids = set(l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in alt_leases)
    p1_ids = set(l.get('LeaseId') or l.get('leaseId') or l.get('Id') or l.get('id') for l in page1_leases)
    if alt_ids and alt_ids != p1_ids:
        print(f"  ✅ page_number/per_page works! Got {len(alt_leases)} different records.")
    else:
        print(f"  page_number/per_page returned {len(alt_leases)} records (same as page 1 = not working).")

print("\n" + "=" * 80)
if total_count_from_meta:
    print(f"CONCLUSION: API reports totalCount = {total_count_from_meta} — use this for counts directly.")
else:
    print("CONCLUSION: No totalCount in metadata. Rely on pagination test results above.")
print("=" * 80)
