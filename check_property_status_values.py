"""
Check PROPERTY_STATUS values for known active properties
"""
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG')
PROPERTIES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"

# Known active properties with lots of leases
ACTIVE_PROPERTIES = [
    '130837',   # Theory U District
    '122966',   # 48 West
    '39760',    # Hawks Landing
    '134939',   # Theory Syracuse
]

def check_property_status():
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Api-Key': API_KEY
    }
    
    payload = {
        "auth": {"type": "apikey"},
        "requestId": str(int(datetime.now().timestamp() * 1000)),
        "method": {
            "name": "getProperties",
            "version": "r1",
            "params": {}
        }
    }
    
    response = requests.post(PROPERTIES_URL, headers=headers, json=payload, timeout=60)
    data = response.json()
    
    result = data.get('response', {}).get('result', {})
    physical_property = result.get('PhysicalProperty', {})
    properties = physical_property.get('Property', [])
    
    if isinstance(properties, dict):
        properties = [properties]
    
    print("="*80)
    print("PROPERTY_STATUS VALUES FOR KNOWN ACTIVE PROPERTIES")
    print("="*80)
    
    for active_id in ACTIVE_PROPERTIES:
        for prop in properties:
            if str(prop.get('PropertyID')) == active_id:
                prop_name = prop.get('MarketingName')
                custom_keys = prop.get('CustomKeysData', {})
                
                print(f"\nProperty: {prop_name} (ID: {active_id})")
                
                if custom_keys:
                    custom_key_list = custom_keys.get('CustomKeyData', [])
                    if isinstance(custom_key_list, dict):
                        custom_key_list = [custom_key_list]
                    
                    for key_data in custom_key_list:
                        print(f"  {key_data.get('Key')}: {key_data.get('Value')}")
                else:
                    print("  NO CustomKeysData")
                break
    
    # Also check all unique PROPERTY_STATUS values
    print("\n" + "="*80)
    print("ALL PROPERTY_STATUS VALUES IN SYSTEM")
    print("="*80)
    
    status_counts = {}
    for prop in properties:
        custom_keys = prop.get('CustomKeysData', {})
        if custom_keys:
            custom_key_list = custom_keys.get('CustomKeyData', [])
            if isinstance(custom_key_list, dict):
                custom_key_list = [custom_key_list]
            
            for key_data in custom_key_list:
                if key_data.get('Key') == 'PROPERTY_STATUS':
                    status_val = key_data.get('Value')
                    status_counts[status_val] = status_counts.get(status_val, 0) + 1
    
    print("\nPROPERTY_STATUS value counts:")
    for status_val, count in sorted(status_counts.items()):
        print(f"  Status '{status_val}': {count} properties")
    
    print(f"\nProperties with NO PROPERTY_STATUS: {346 - sum(status_counts.values())}")

if __name__ == "__main__":
    check_property_status()
