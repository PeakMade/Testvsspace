"""
Test standard vs external Entrata API endpoints with correct auth
"""
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

# Test 1: Standard API endpoint with apikey auth
print("="*80)
print("Test 1: Standard API - https://{org}.entrata.com/api/v1")
print("="*80)
url = f"https://{ORG}.entrata.com/api/v1/properties"
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
    response = requests.post(url, headers=headers, json=payload, timeout=15)
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

# Test 2: External API with searchProperties r1
print("="*80)
print("Test 2: External API - searchProperties r1")
print("="*80)
url = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"
payload = {
    "auth": {"type": "apikey"},
    "requestId": str(int(datetime.now().timestamp() * 1000)),
    "method": {
        "name": "searchProperties",
        "version": "r1",
        "params": {}
    }
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=15)
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

# Test 3: External API with getProperties r1
print("="*80)
print("Test 3: External API - getProperties r1")
print("="*80)
url = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"
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
    response = requests.post(url, headers=headers, json=payload, timeout=15)
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
