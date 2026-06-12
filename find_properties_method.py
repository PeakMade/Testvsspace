"""
Test to find the correct properties method name
"""
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
BASE_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1"

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

# Try different method names
methods = [
    ("searchProperties", "properties"),
    ("getPropertyList", "properties"),
    ("listProperties", "properties"),
    ("getProperties", "properties"),
    ("searchLeases", "leases"),
]

for method_name, endpoint in methods:
    print("="*80)
    print(f"Testing: {method_name} on /{endpoint}")
    print("="*80)
    
    url = f"{BASE_URL}/{endpoint}"
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": method_name,
            "version": "r2",
            "params": {}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}: {error['message']}")
        else:
            print(f"✅ SUCCESS! Response preview:")
            print(json.dumps(data, indent=2)[:500])
            break
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()
