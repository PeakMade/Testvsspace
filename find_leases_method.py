"""
Try to get leases without specifying propertyId to see all properties
"""
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
LEASES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

# Try 1: Get leases with status=1 (Pending) without propertyId
print("="*80)
print("Attempt 1: getLeases with leaseStatus=1, no propertyId")
print("="*80)
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeases",
        "version": "r2",
        "params": {
            "leaseStatus": 1
        }
    }
}

try:
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
    data = response.json()
    print(f"Status: {response.status_code}")
    
    if 'error' in data.get('response', {}):
        error = data['response']['error']
        print(f"❌ Error {error['code']}: {error['message']}")
    else:
        print(f"✅ SUCCESS!")
        print(json.dumps(data, indent=2)[:1000])
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n")

# Try 2: searchLeases
print("="*80)
print("Attempt 2: searchLeases with leaseStatusTypeIds=1")
print("="*80)
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "searchLeases",
        "version": "r2",
        "params": {
            "leaseStatusTypeIds": "1"
        }
    }
}

try:
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
    data = response.json()
    print(f"Status: {response.status_code}")
    
    if 'error' in data.get('response', {}):
        error = data['response']['error']
        print(f"❌ Error {error['code']}: {error['message']}")
    else:
        print(f"✅ SUCCESS!")
        print(json.dumps(data, indent=2)[:1000])
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n")

# Try 3: getLeaseDetails with minimal params
print("="*80)
print("Attempt 3: getLeaseDetails with just leaseStatusTypeIds")
print("="*80)
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "getLeaseDetails",
        "version": "r2",
        "params": {
            "leaseStatusTypeIds": "1"
        }
    }
}

try:
    response = requests.post(LEASES_URL, headers=headers, json=payload, timeout=30)
    data = response.json()
    print(f"Status: {response.status_code}")
    
    if 'error' in data.get('response', {}):
        error = data['response']['error']
        print(f"❌ Error {error['code']}: {error['message']}")
    else:
        print(f"✅ SUCCESS!")
        print(json.dumps(data, indent=2)[:1000])
except Exception as e:
    print(f"❌ Exception: {e}")
