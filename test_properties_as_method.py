"""
Test using 'properties' as method name
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

test_cases = [
    # Try 'properties' as method name on base endpoint
    (f"https://apis.entrata.com/ext/orgs/{ORG}/v1", "properties", "r1"),
    (f"https://apis.entrata.com/ext/orgs/{ORG}/v1", "properties", "r2"),
    
    # Try without 'get' prefix
    (f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties", "properties", "r1"),
    (f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties", "properties", "r2"),
]

for idx, test in enumerate(test_cases, 1):
    url, method_name, version = test
    
    print("=" * 80)
    print(f"Test {idx}: method='{method_name}' version={version}")
    print(f"URL: {url}")
    print("=" * 80)
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": method_name,
            "version": version,
            "params": {}
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        
        print(f"\nStatus: {response.status_code}")
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}: {error['message']}")
        elif 'result' in data.get('response', {}):
            print(f"✅✅✅ SUCCESS! ✅✅✅")
            print(json.dumps(data, indent=2)[:2000])
            break
        else:
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)[:200]}")
    
    print()

print("Test complete.")
