"""
Test getProperties based on API documentation
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

# Test multiple URL formats and versions
test_configs = [
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "r1"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "r2"),
    ("https://apis.entrata.com/ext/orgs/{}/v1/properties".format(ORG), "r3"),
    ("https://apis.entrata.com/{}/v1/properties".format(ORG), "r1"),
    ("https://apis.entrata.com/{}/v1/properties".format(ORG), "r2"),
]

for idx, (url, version) in enumerate(test_configs, 1):
    print("=" * 80)
    print(f"Test {idx}: getProperties version {version}")
    print("=" * 80)
    print(f"URL: {url}")
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getProperties",
            "version": version,
            "params": {}
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        print(f"Status: {response.status_code}")
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}: {error['message']}")
        elif 'result' in data.get('response', {}):
            result = data['response']['result']
            print(f"✅✅✅ SUCCESS! ✅✅✅")
            
            # Try to extract properties
            properties = []
            if 'Property' in result:
                properties = result['Property']
                if isinstance(properties, dict):
                    properties = [properties]
            elif 'Properties' in result:
                properties = result['Properties']
                if isinstance(properties, dict):
                    properties = properties.get('Property', [])
            
            print(f"\nFound {len(properties)} properties!")
            print(f"\nFull response:")
            print(json.dumps(data, indent=2)[:3000])
            
            # Save to file
            with open('properties.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✓ Saved full response to properties.json")
            break
        else:
            print(f"Response: {json.dumps(data, indent=2)[:1000]}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print()
