"""Test correct Entrata API structure"""
import requests
import json

username = "pbatson@peakmade-test-17291"
password = "PeakMade12!"
base_url = "https://peakmade-test-17291.entrata.com/api/v1"

# Entrata uses method-specific endpoints
test_cases = [
    {
        "name": "getProperties",
        "url": f"{base_url}/getproperties",
        "payload": {
            "auth": {
                "type": "basic"
            },
            "requestId": "1",
            "method": {
                "name": "getProperties",
                "version": "r1",
                "params": {}
            }
        }
    },
    {
        "name": "getProperties (alternative)",
        "url": base_url,
        "payload": {
            "auth": {
                "type": "basic"
            },
            "requestId": "1",
            "method": {
                "name": "getProperties",
                "version": "r1"
            }
        }
    }
]

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

print("Testing Entrata API methods...\n")

for test in test_cases:
    print(f"Testing: {test['name']}")
    print(f"URL: {test['url']}")
    try:
        response = requests.post(
            test['url'],
            auth=(username, password),
            headers=headers,
            json=test['payload'],
            timeout=10
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ Response received")
                print(json.dumps(data, indent=2)[:500])
                
                # Check for successful response
                if 'response' in data:
                    if 'error' in data['response']:
                        print(f"\n⚠ API Error: {data['response']['error']}")
                    elif 'result' in data['response']:
                        print(f"\n✓✓ SUCCESS! API call worked!")
                        break
            except:
                print(f"Response text: {response.text[:200]}")
        else:
            print(f"Error: {response.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")
    print("\n" + "="*80 + "\n")
