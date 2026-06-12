"""
Test getApplications method to find pending applications
"""
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Api-Key': API_KEY
}

# Try different possible endpoints and method names for applications
test_configs = [
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/applications",
        "method": "getApplications",
        "version": "r1"
    },
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/applications",
        "method": "getApplications",
        "version": "r2"
    },
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/leases",
        "method": "getApplications",
        "version": "r1"
    },
    {
        "url": f"https://apis.entrata.com/ext/orgs/{ORG}/v1/residents",
        "method": "getApplications",
        "version": "r1"
    },
]

TEST_PROPERTY_ID = "100165016"  # 1540 Place

print("=" * 80)
print("TESTING getApplications METHOD")
print("=" * 80)
print(f"Test Property: 1540 Place (ID: {TEST_PROPERTY_ID})")
print()

for idx, config in enumerate(test_configs, 1):
    print(f"Test {idx}: {config['method']} v{config['version'][-1]}")
    print(f"URL: {config['url']}")
    print("-" * 80)
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": config['method'],
            "version": config['version'],
            "params": {
                "propertyId": TEST_PROPERTY_ID
            }
        }
    }
    
    try:
        response = requests.post(config['url'], headers=headers, json=payload, timeout=30)
        data = response.json()
        
        if 'error' in data.get('response', {}):
            error = data['response']['error']
            print(f"❌ Error {error['code']}: {error['message']}")
        elif 'result' in data.get('response', {}):
            result = data['response']['result']
            print(f"✅ SUCCESS!")
            print(f"Response keys: {list(result.keys())}")
            print(f"Full response:")
            print(json.dumps(data, indent=2)[:2000])
            break
        else:
            print(f"Response: {json.dumps(data, indent=2)[:500]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print()

print()
print("=" * 80)
print("If all tests failed, applications might be under a different method name.")
print("Common alternatives: getGuestcards, getProspects, getPendingApplications")
print("=" * 80)
