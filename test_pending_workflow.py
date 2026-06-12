"""
Test the complete workflow: getProperties -> getLeases (status=1)
This shows the exact API calls needed once Error 420 is resolved
"""

import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration - Use correct Entrata API endpoint
API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG', 'peakmade')
BASE_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1"
PROPERTIES_URL = f"{BASE_URL}/properties"
LEASES_URL = f"{BASE_URL}/leases"

if not API_KEY:
    print("❌ Error: ENTRATA_API_KEY not found in .env file")
    exit(1)

def test_get_properties():
    """Test getProperties API call"""
    print("=" * 80)
    print("STEP 1: Testing getProperties")
    print("=" * 80)
    
    payload = {
        "auth": {
            "type": "apikey"
        },
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getProperties",
            "version": "r2",
            "params": {}
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    
    print(f"URL: {PROPERTIES_URL}")
    print(f"Using X-Api-Key header authentication")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(
            PROPERTIES_URL,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response:")
            print(json.dumps(data, indent=2)[:500])
            
            # Check for errors
            if 'response' in data and 'error' in data['response']:
                error = data['response']['error']
                print(f"\n❌ API Error {error['code']}: {error['message']}")
                return None
            
            # Extract properties
            if 'response' in data and 'result' in data['response']:
                result = data['response']['result']
                properties = []
                
                if 'Properties' in result:
                    properties = result['Properties'].get('Property', [])
                elif 'Property' in result:
                    properties = result['Property']
                
                if isinstance(properties, dict):
                    properties = [properties]
                
                print(f"\n✅ Success! Found {len(properties)} properties")
                return properties
        else:
            print(f"Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    return None

def test_get_leases(property_id):
    """Test getLeases API call for a specific property with status=1 (Pending)"""
    print("\n" + "=" * 80)
    print(f"STEP 2: Testing getLeases for Property ID: {property_id}")
    print("=" * 80)
    
    payload = {
        "auth": {
            "type": "apikey"
        },
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getLeases",
            "version": "r2",
            "params": {
                "propertyIds": [str(property_id)],
                "leaseStatus": 1  # 1 = Pending
            }
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    
    print(f"URL: {LEASES_URL}")
    print(f"Using X-Api-Key header authentication")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        response = requests.post(
            LEASES_URL,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response:")
            print(json.dumps(data, indent=2)[:500])
            
            # Check for errors
            if 'response' in data and 'error' in data['response']:
                error = data['response']['error']
                print(f"\n❌ API Error {error['code']}: {error['message']}")
                return None
            
            # Extract leases
            if 'response' in data and 'result' in data['response']:
                result = data['response']['result']
                leases = []
                
                if 'Leases' in result:
                    leases = result['Leases'].get('Lease', [])
                elif 'Lease' in result:
                    leases = result['Lease']
                
                if isinstance(leases, dict):
                    leases = [leases]
                
                print(f"\n✅ Success! Found {len(leases)} pending lease(s)")
                return leases
        else:
            print(f"Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    return None

def main():
    print("ENTRATA API WORKFLOW TEST: getProperties -> getLeases (Pending)")
    print()
    
    # Step 1: Get all properties
    properties = test_get_properties()
    
    if not properties:
        print("\n" + "=" * 80)
        print("⚠️  BLOCKED: Cannot proceed without properties")
        print("=" * 80)
        print("\nCurrent Issue: Error 420 - API Agreement Required")
        print("Contact: partner-integrations@entrata.com or apisupport@entrata.com")
        print("\nOnce resolved, this workflow will:")
        print("1. Get all properties from your portfolio")
        print("2. For each property, get leases with status=1 (Pending)")
        print("3. Count pending leases per property")
        print("4. Generate Excel report")
        return
    
    # Step 2: Test getLeases for first property
    if len(properties) > 0:
        first_property = properties[0]
        property_id = (first_property.get('PropertyId') or 
                      first_property.get('propertyId') or 
                      first_property.get('id'))
        
        if property_id:
            leases = test_get_leases(property_id)
            
            if leases is not None:
                print("\n" + "=" * 80)
                print("✅ COMPLETE WORKFLOW TEST SUCCESSFUL!")
                print("=" * 80)
                print("\nThe entrata_pending_leases.py script will now work.")
                print("Run: python entrata_pending_leases.py")

if __name__ == "__main__":
    main()
