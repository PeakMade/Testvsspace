"""
Get ALL status=1 leases for 48 West (handle 500-record API limit with pagination)
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

PROPERTY_ID = "1122966"  # 48 West
PROPERTY_NAME = "48 WEST"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

print("=" * 80)
print(f"GET ALL STATUS=1 LEASES: {PROPERTY_NAME}")
print("=" * 80)
print()

# Try pagination with offset/limit
print("Attempting to get all leases with pagination...")
print("-" * 80)

all_leases = []
offset = 0
limit = 500
page = 1

while True:
    print(f"\nPage {page}: offset={offset}, limit={limit}")
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getLeases",
            "version": "r2",
            "params": {
                "propertyId": PROPERTY_ID,
                "leaseStatusTypeIds": "1",
                "offset": offset,
                "limit": limit
            }
        }
    }
    
    try:
        response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=60)
        data = response.json()
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}: {error['message']}")
            break
        
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
        print(f"  ✓ Retrieved {count} leases (total so far: {len(all_leases) + count})")
        
        if count == 0:
            print("  No more leases returned - stopping")
            break
        
        all_leases.extend(leases)
        
        # If we got less than the limit, we've reached the end
        if count < limit:
            print(f"  ✓ Got {count} < {limit} - reached end of data")
            break
        
        # Move to next page
        offset += limit
        page += 1
        
        # Safety check
        if page > 20:
            print("⚠️  Safety limit: stopped after 20 pages (10,000 records)")
            break
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        break

print()
print("=" * 80)
print("FINAL RESULTS:")
print("=" * 80)
print(f"Total status=1 leases for {PROPERTY_NAME}: {len(all_leases)}")

if all_leases:
    # Show sample lease structure
    print("\nSample lease (first record):")
    print(json.dumps(all_leases[0], indent=2)[:1500])
    
    # Analyze dates
    print("\n" + "=" * 80)
    print("DATE ANALYSIS:")
    print("=" * 80)
    
    from datetime import date
    
    move_in_dates = []
    start_dates = []
    
    for lease in all_leases:
        # Move-in date
        move_in = lease.get('MoveInDate', lease.get('moveInDate', ''))
        if move_in:
            try:
                if '/' in move_in:
                    parts = move_in.split('/')
                    move_in_dates.append(date(int(parts[2]), int(parts[0]), int(parts[1])))
                elif '-' in move_in:
                    move_in_dates.append(date.fromisoformat(move_in.split('T')[0]))
            except:
                pass
        
        # Start date
        start = lease.get('StartDate', lease.get('LeaseStartDate', ''))
        if start:
            try:
                if '/' in start:
                    parts = start.split('/')
                    start_dates.append(date(int(parts[2]), int(parts[0]), int(parts[1])))
                elif '-' in start:
                    start_dates.append(date.fromisoformat(start.split('T')[0]))
            except:
                pass
    
    if move_in_dates:
        move_in_dates.sort()
        print(f"Move-in dates: {move_in_dates[0]} to {move_in_dates[-1]}")
    
    if start_dates:
        start_dates.sort()
        print(f"Lease start dates: {start_dates[0]} to {start_dates[-1]}")
    
    # Count for 2026-2027 academic year
    acad_start = date(2026, 8, 1)
    acad_end = date(2027, 7, 31)
    
    acad_move_in = [d for d in move_in_dates if acad_start <= d <= acad_end]
    acad_start_dates = [d for d in start_dates if acad_start <= d <= acad_end]
    
    print(f"\nLeases with move-in dates in 2026-2027 academic year: {len(acad_move_in)}")
    print(f"Leases with start dates in 2026-2027 academic year: {len(acad_start_dates)}")

print()
print("=" * 80)
if len(all_leases) >= 700 and len(all_leases) <= 750:
    print(f"🎯 MATCH! {len(all_leases)} is close to Peak Campus number (714)")
elif len(all_leases) >= 900 and len(all_leases) <= 950:
    print(f"🎯 MATCH! {len(all_leases)} is close to Peak Campus number (920)")
else:
    print(f"Total: {len(all_leases)} status=1 leases (compare to Peak Campus: 714/920)")
