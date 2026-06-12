"""
Test Entrata API with updated format (post-agreement)
"""

import requests
import json

username = "pbatson@peakmade-test-17291"
password = "PeakMade12!"
base_domain = "https://peakmade-test-17291.entrata.com"

# Try updated API formats
test_configs = [
    {
        "name": "New API - getProperties",
        "url": f"{base_domain}/api/v1/properties",
        "method": "GET",
        "payload": None
    },
    {
        "name": "New API - leases",  
        "url": f"{base_domain}/api/v1/leases",
        "method": "GET",
        "payload": None
    },
    {
        "name": "REST API - properties",
        "url": f"{base_domain}/api/v1/properties",
        "method": "POST",
        "payload": {"requestId": "1"}
    },
    {
        "name": "REST API - leases with filters",
        "url": f"{base_domain}/api/v1/leases",
        "method": "POST",
        "payload": {
            "requestId": "1",
            "filters": {"leaseStatus": 1}
        }
    },
    {
        "name": "GraphQL Style",
        "url": f"{base_domain}/api/graphql",
        "method": "POST",
        "payload": {
            "query": "{ properties { id name } }"
        }
    }
]

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Python/Entrata-Integration'
}

print("=" * 80)
print("TESTING UPDATED ENTRATA API FORMATS")
print("=" * 80)
print(f"Note: Your account needs to accept the new API agreement.")
print(f"Contact: partner-integrations@entrata.com or apisupport@entrata.com")
print("=" * 80)

for idx, config in enumerate(test_configs, 1):
    print(f"\n[{idx}/{len(test_configs)}] {config['name']}")
    print(f"Method: {config['method']}")
    print(f"URL: {config['url']}")
    
    try:
        if config['method'] == 'GET':
            response = requests.get(
                config['url'],
                auth=(username, password),
                headers=headers,
                timeout=15
            )
        else:
            response = requests.post(
                config['url'],
                auth=(username, password),
                headers=headers,
                json=config['payload'],
                timeout=15
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                print("✓ JSON Response received")
                
                # Check response structure
                if 'error' in data or ('response' in data and 'error' in data['response']):
                    error_data = data.get('error') or data['response'].get('error')
                    error_code = error_data.get('code', 'N/A')
                    error_msg = error_data.get('message', 'Unknown error')
                    
                    print(f"  ⚠️  API Error {error_code}: {error_msg}")
                    
                    if error_code != 420:  # Different error = progress!
                        print(f"  📋 Full response: {json.dumps(data, indent=2)[:400]}")
                else:
                    print("  ✓✓ SUCCESS! Valid response received!")
                    print(f"  Response preview: {json.dumps(data, indent=2)[:400]}")
                    print("\n" + "=" * 80)
                    print("WORKING CONFIGURATION FOUND!")
                    print("=" * 80)
                    break
                    
            except json.JSONDecodeError:
                print(f"  Non-JSON response: {response.text[:200]}")
        elif response.status_code == 401:
            print("  ⚠️  Authentication failed - check credentials")
        elif response.status_code == 403:
            print("  ⚠️  Access forbidden - API agreement may need acceptance")
        elif response.status_code == 404:
            print("  ⚠️  Endpoint not found")
        else:
            print(f"  Response: {response.text[:150]}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:150]}")
    
    print()

print("=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("If all tests show error 420, your Entrata account needs to:")
print("1. Accept the new API agreement")
print("2. Contact partner-integrations@entrata.com")
print("3. Get updated API documentation for your account")
print("=" * 80)
