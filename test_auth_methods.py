"""
Test different authentication methods with Entrata API
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
URL = f"https://{ORG}.entrata.com/api/v1/properties"

print("Testing different authentication methods...\n")

# Method 1: API Key in X-API-Key Header
print("="*80)
print("METHOD 1: X-API-Key Header")
print("="*80)
try:
    response = requests.post(
        URL,
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY
        },
        json={
            "auth": {"type": "basic"},
            "requestId": "1",
            "method": {"name": "getProperties", "version": "r1", "params": {}}
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Method 2: Authorization Bearer Token
print("="*80)
print("METHOD 2: Authorization Bearer Token")
print("="*80)
try:
    response = requests.post(
        URL,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        },
        json={
            "auth": {"type": "basic"},
            "requestId": "1",
            "method": {"name": "getProperties", "version": "r1", "params": {}}
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Method 3: API Key in payload auth
print("="*80)
print("METHOD 3: API Key in Auth Credentials Object")
print("="*80)
try:
    response = requests.post(
        URL,
        headers={'Content-Type': 'application/json'},
        json={
            "auth": {
                "type": "basic",
                "credentials": {
                    "username": API_KEY
                }
            },
            "requestId": "1",
            "method": {"name": "getProperties", "version": "r1", "params": {}}
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Method 4: API Key in custom header
print("="*80)
print("METHOD 4: Entrata-API-Key Header")
print("="*80)
try:
    response = requests.post(
        URL,
        headers={
            'Content-Type': 'application/json',
            'Entrata-API-Key': API_KEY
        },
        json={
            "auth": {"type": "basic"},
            "requestId": "1",
            "method": {"name": "getProperties", "version": "r1", "params": {}}
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}\n")
except Exception as e:
    print(f"Error: {e}\n")

# Method 5: Try without auth type in payload
print("="*80)
print("METHOD 5: HTTP Basic Auth (no auth in payload)")
print("="*80)
try:
    response = requests.post(
        URL,
        auth=(API_KEY, ''),
        headers={'Content-Type': 'application/json'},
        json={
            "requestId": "1",
            "method": {"name": "getProperties", "version": "r1", "params": {}}
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}\n")
except Exception as e:
    print(f"Error: {e}\n")
