"""
Check the 3 properties with 0 leases (not marked as closed) 
to see if we can identify whether they're new/active or just placeholders
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

# The 3 properties with 0 leases that aren't marked as closed
ZERO_LEASE_IDS = [
    ('100126326', 'Kenect Nashville'),
    ('100154189', 'Lakeshore Towers'),
    ('100168545', 'Olathe Commons')
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


def analyze_zero_lease_properties():
    """Analyze properties with 0 leases to identify if they're active or placeholder"""
    print("="*80)
    print("ANALYZING PROPERTIES WITH 0 LEASES")
    print("="*80)
    
    all_properties = get_all_properties()
    
    if not all_properties:
        print("❌ Could not retrieve properties")
        return
    
    print(f"\n✓ Retrieved {len(all_properties)} total properties\n")
    
    # Indicators of an active/operational property:
    indicators = [
        'YearBuilt',
        'PropertyHours', 
        'webSite',
        'LongDescription',
        'ShortDescription',
        'LeaseTerms',
        'CustomKeysData'
    ]
    
    for prop_id, prop_name in ZERO_LEASE_IDS:
        print("="*80)
        print(f"Property: {prop_name} (ID: {prop_id})")
        print("="*80)
        
        found = False
        for prop in all_properties:
            if str(prop.get('PropertyID')) == prop_id:
                found = True
                
                # Check key indicators
                print(f"\n📊 Activity Indicators:")
                print(f"  Type: {prop.get('Type', 'N/A')}")
                print(f"  IsDisabled: {prop.get('IsDisabled', 'N/A')}")
                print(f"  YearBuilt: {prop.get('YearBuilt', 'NOT SET')}")
                print(f"  Has Website: {'YES' if prop.get('webSite') else 'NO'}")
                print(f"  Has PropertyHours: {'YES' if prop.get('PropertyHours') else 'NO'}")
                print(f"  Has Description: {'YES' if prop.get('LongDescription') or prop.get('ShortDescription') else 'NO'}")
                print(f"  Has LeaseTerms: {'YES' if prop.get('LeaseTerms') else 'NO'}")
                
                # Check custom keys for property status
                custom_keys = prop.get('CustomKeysData', {})
                if custom_keys:
                    custom_key_list = custom_keys.get('CustomKeyData', [])
                    if isinstance(custom_key_list, dict):
                        custom_key_list = [custom_key_list]
                    
                    print(f"\n🔑 Custom Keys:")
                    for key_data in custom_key_list:
                        print(f"  {key_data.get('Key')}: {key_data.get('Value')}")
                else:
                    print(f"\n🔑 Custom Keys: NONE")
                
                # Address
                addresses = prop.get('Addresses', {})
                if addresses:
                    addr_list = addresses.get('Address', [])
                    if isinstance(addr_list, dict):
                        addr_list = [addr_list]
                    if addr_list:
                        addr = addr_list[0]
                        print(f"\n📍 Location:")
                        print(f"  {addr.get('Address', '')}")
                        print(f"  {addr.get('City', '')}, {addr.get('StateCode', '')} {addr.get('PostalCode', '')}")
                
                # Property Hours detail
                if prop.get('PropertyHours'):
                    hours = prop.get('PropertyHours', {}).get('OfficeHours', {}).get('OfficeHour', [])
                    if hours:
                        print(f"\n🕐 Office Hours: {len(hours)} days configured")
                
                # Determine likely status
                print(f"\n💡 Assessment:")
                has_activity_indicators = (
                    prop.get('YearBuilt') or 
                    prop.get('PropertyHours') or 
                    prop.get('webSite') or
                    prop.get('LongDescription') or
                    prop.get('LeaseTerms')
                )
                
                if has_activity_indicators:
                    print(f"  ✓ LIKELY OPERATIONAL - Has marketing/operational data")
                    print(f"  → Recommendation: KEEP (might be pre-leasing or new property)")
                else:
                    print(f"  ⚠️ LIKELY PLACEHOLDER - Missing marketing/operational data")
                    print(f"  → Recommendation: EXCLUDE (probably never went live)")
                
                print("="*80)
                print()
                break
        
        if not found:
            print(f"❌ Property ID {prop_id} not found in Entrata\n")


if __name__ == "__main__":
    analyze_zero_lease_properties()
