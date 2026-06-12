"""
Comprehensive search for getProperties method with all variations
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

# Test combinations of endpoints, methods, and versions
test_cases = [
    # External API with different versions
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "getProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "getProperties", "r2"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "getPropertyList", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "getPropertyList", "r2"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "searchProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "searchProperties", "r2"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "listProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "listProperties", "r2"),
    
    # Try with empty params vs no params
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "getProperties", "r1", {}),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "getProperties", "r2", {}),
    
    # Try property endpoint
    ("https://apis.entrata.com/ext/orgs/{}/v1/property".format(ORG), "getProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/property".format(ORG), "getProperties", "r2"),
]

for idx, test in enumerate(test_cases, 1):
    url = test[0]
    method = test[1]
    version = test[2]
    params = test[3] if len(test) > 3 else None
    
    print("=" * 80)
    print(f"Test {idx}: {method} v{version}")
    print(f"URL: {url}")
    print("=" * 80)
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": method,
            "version": version
        }
    }
    
    if params is not None:
        payload["method"]["params"] = params
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        
        print(f"Status: {response.status_code}")
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}: {error['message']}")
        elif 'result' in data.get('response', {}):
            print(f"✅✅✅ SUCCESS! ✅✅✅")
            print(json.dumps(data, indent=2)[:1500])
            print("\n" + "=" * 80)
            print(f"WORKING METHOD FOUND: {method} version {version}")
            print(f"URL: {url}")
            print("=" * 80)
            break
        else:
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout")
    except Exception as e:
        print(f"❌ Exception: {str(e)[:200]}")
    
    print()

print("\nSearch complete.")
