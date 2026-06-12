"""
Test getProperties on BASE endpoints (not /properties)
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

# Try posting to BASE endpoints (without /properties)
test_cases = [
    # External API base endpoint
    ("https://apis.entrata.com/ext/orgs/{}/v1".format(ORG), "getProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1".format(ORG), "getProperties", "r2"),
    
    # Standard API base endpoint
    ("https://{}.entrata.com/api/v1".format(ORG), "getProperties", "r1"),
    ("https://{}.entrata.com/api/v1".format(ORG), "getProperties", "r2"),
    
    # Try without version in URL
    ("https://apis.entrata.com/ext/orgs/{}".format(ORG), "getProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}".format(ORG), "getProperties", "r2"),
    
    # Try property-management endpoint
    ("https://apis.entrata.com/ext/orgs/{}/v1/property-management".format(ORG), "getProperties", "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/property-management".format(ORG), "getProperties", "r2"),
]

for idx, test in enumerate(test_cases, 1):
    url = test[0]
    method = test[1]
    version = test[2]
    
    print("=" * 80)
    print(f"Test {idx}: {method} v{version}")
    print(f"URL: {url}")
    print("=" * 80)
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": method,
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
            result = data['response']['result']
            print(f"✅✅✅ SUCCESS! ✅✅✅")
            print(f"Result keys: {list(result.keys())}")
            print(json.dumps(data, indent=2)[:2000])
            print("\n" + "=" * 80)
            print(f"WORKING CONFIGURATION:")
            print(f"  URL: {url}")
            print(f"  Method: {method}")
            print(f"  Version: {version}")
            print("=" * 80)
            break
        else:
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout (20 seconds)")
    except Exception as e:
        print(f"❌ Exception: {str(e)[:300]}")
    
    print()

print("\nTest complete.")
