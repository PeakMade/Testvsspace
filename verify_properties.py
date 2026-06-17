"""
Verify properties by examining full Entrata API response
Check what fields might distinguish vendors/inactive properties
"""
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import json

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG')
PROPERTIES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"

# Properties to examine (from screenshot - 0 lease properties)
SUSPECT_PROPERTY_IDS = [
    '1122493',  # BVSHSSF PE MEMBER, LP (known vendor)
    '100090963', # College Crossing at National
    '100090964', # Greyhound Village
    '100126326', # Kenect Nashville
    '100154189', # Lakeshore Towers
    '100168545', # Olathe Commons
    '100013335', # Solaire Oxford
    '1183571',   # The Manor
    '100090965'  # University Lofts
]

def get_all_properties():
    """Get all properties from Entrata API"""
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
    
    try:
        response = requests.post(PROPERTIES_URL, headers=headers, json=payload, timeout=60)
        data = response.json()
        
        if 'error' in data.get('response', {}):
            print(f"❌ API Error: {data['response']['error']}")
            return []
        
        result = data.get('response', {}).get('result', {})
        physical_property = result.get('PhysicalProperty', {})
        properties = physical_property.get('Property', [])
        
        if isinstance(properties, dict):
            properties = [properties]
        
        return properties
        
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return []


def examine_suspect_properties():
    """Examine the suspect properties in detail"""
    print("="*80)
    print("EXAMINING SUSPECT PROPERTIES (0 LEASES)")
    print("="*80)
    
    all_properties = get_all_properties()
    
    if not all_properties:
        print("❌ Could not retrieve properties from Entrata")
        return
    
    print(f"\n✓ Retrieved {len(all_properties)} total properties from Entrata\n")
    
    # Find and examine each suspect property
    for suspect_id in SUSPECT_PROPERTY_IDS:
        found = False
        for prop in all_properties:
            if str(prop.get('PropertyID')) == suspect_id:
                found = True
                print("="*80)
                print(f"Property ID: {suspect_id}")
                print(f"Name: {prop.get('MarketingName', 'N/A')}")
                print("-"*80)
                
                # Print all available fields
                for key, value in sorted(prop.items()):
                    if key not in ['PropertyID', 'MarketingName']:  # Already printed these
                        print(f"{key}: {value}")
                
                print("="*80)
                print()
                break
        
        if not found:
            print(f"❌ Property ID {suspect_id} NOT FOUND in Entrata response\n")
    
    # Also check if there are any common fields that distinguish these
    print("\n" + "="*80)
    print("SUMMARY: Looking for distinguishing patterns")
    print("="*80)
    
    suspect_props = []
    for suspect_id in SUSPECT_PROPERTY_IDS:
        for prop in all_properties:
            if str(prop.get('PropertyID')) == suspect_id:
                suspect_props.append(prop)
                break
    
    if suspect_props:
        # Check what fields are common
        print(f"\nFound {len(suspect_props)} of {len(SUSPECT_PROPERTY_IDS)} suspect properties")
        
        # Check IsDisabled values
        disabled_values = [p.get('IsDisabled', 'N/A') for p in suspect_props]
        print(f"\nIsDisabled values: {disabled_values}")
        
        # Check if there's a Type field
        if 'Type' in suspect_props[0]:
            type_values = [p.get('Type', 'N/A') for p in suspect_props]
            print(f"Type values: {type_values}")
        
        # Print all unique keys across these properties
        all_keys = set()
        for prop in suspect_props:
            all_keys.update(prop.keys())
        
        print(f"\nAll fields available in these properties:")
        for key in sorted(all_keys):
            print(f"  - {key}")


if __name__ == "__main__":
    examine_suspect_properties()
