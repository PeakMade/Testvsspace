"""
Test posting to /properties endpoint with different payload structures
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
    # Test 1: POST to /properties with no method name (endpoint IS the method)
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties",
        "payload": {
            "auth": {"type": "apikey"},
            "requestId": str(int(datetime.now().timestamp() * 1000))
        }
    },
    # Test 2: POST to /properties with empty method
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties",
        "payload": {
            "auth": {"type": "apikey"},
            "requestId": str(int(datetime.now().timestamp() * 1000)),
            "method": {}
        }
    },
    # Test 3: GET request to /properties
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties",
        "method": "GET"
    },
    # Test 4: POST with just params, no method name
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties",
        "payload": {
            "auth": {"type": "apikey"},
            "requestId": str(int(datetime.now().timestamp() * 1000)),
            "params": {}
        }
    },
    # Test 5: Minimal payload
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties",
        "payload": {}
    },
]

for idx, test in enumerate(test_cases, 1):
    print("=" * 80)
    print(f"Test {idx}")
    print("=" * 80)
    print(f"URL: {test['url']}")
    
    try:
        if test.get('method') == 'GET':
            print("Method: GET")
            response = requests.get(test['url'], headers=headers, timeout=20)
        else:
            print(f"Method: POST")
            print(f"Payload: {json.dumps(test.get('payload', {}), indent=2)}")
            response = requests.post(
                test['url'], 
                headers=headers, 
                json=test.get('payload', {}), 
                timeout=20
            )
        
        print(f"\nStatus: {response.status_code}")
        
        try:
            data = response.json()
            
            if 'error' in data.get('response', {}):
                error = data['response']['error']
                print(f"❌ Error {error['code']}: {error['message']}")
            elif 'result' in data.get('response', {}):
                result = data['response']['result']
                print(f"✅✅✅ SUCCESS! ✅✅✅")
                print(f"Result preview:")
                print(json.dumps(data, indent=2)[:2000])
                print("\n" + "=" * 80)
                print("WORKING CONFIGURATION FOUND!")
                print("=" * 80)
                break
            else:
                print(f"Response: {json.dumps(data, indent=2)[:800]}")
        except:
            print(f"Non-JSON Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout")
    except Exception as e:
        print(f"❌ Exception: {str(e)[:300]}")
    
    print()

print("Test complete.")
