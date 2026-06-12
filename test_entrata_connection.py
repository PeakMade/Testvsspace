"""Test different Entrata API endpoints"""
import requests

username = "pbatson@peakmade-test-17291"
password = "PeakMade12!"
base_domain = "https://peakmade-test-17291.entrata.com"

# Common Entrata API endpoint variations
endpoints = [
    f"{base_domain}/api/v1",
    f"{base_domain}/api/v1/json",
    f"{base_domain}/api/json",
    f"{base_domain}/api",
    f"{base_domain}/api/rpc",
]

test_payload = {
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

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

print("Testing Entrata API endpoints...\n")

for endpoint in endpoints:
    print(f"Testing: {endpoint}")
    try:
        response = requests.post(
            endpoint,
            auth=(username, password),
            headers=headers,
            json=test_payload,
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ SUCCESS! This endpoint works.")
            print(f"  Response preview: {str(response.json())[:200]}...")
            break
        else:
            print(f"  Response: {response.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()
