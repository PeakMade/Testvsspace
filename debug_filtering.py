"""
Debug property filtering to see what's being excluded and why
"""
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('ENTRATA_API_KEY')
ORG = os.getenv('ENTRATA_ORG')
PROPERTIES_URL = f"https://apis.entrata.com/ext/orgs/{ORG}/v1/properties"

def get_properties_with_debug():
    """Get properties and show filtering reasons"""
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
        
        result = data.get('response', {}).get('result', {})
        physical_property = result.get('PhysicalProperty', {})
        properties = physical_property.get('Property', [])
        
        if isinstance(properties, dict):
            properties = [properties]
        
        print(f"Total properties from API: {len(properties)}\n")
        
        # Track filtering reasons
        filtered_counts = {
            'disabled': 0,
            'corporate': 0,
            'status_2': 0,
            'no_name': 0,
            'starts_z': 0,
            'keyword': 0,
            'canadian': 0,
            'no_operational': 0,
            'kept': 0
        }
        
        exclude_keywords = ['retail', 'reit', 'llc', 'corporate', 'shuttle', 'condominium', 'assoc', 'master', 'ucc', 'university center', 'gateway', 'connect', 'member', ' lp', ' pe']
        
        kept_sample = []
        no_op_sample = []
        
        for prop in properties:
            prop_name = prop.get('MarketingName', '')
            prop_id = prop.get('PropertyID')
            is_disabled = prop.get('IsDisabled', 0)
            prop_type = prop.get('Type', '')
            
            if is_disabled == 1:
                filtered_counts['disabled'] += 1
                continue
            
            if prop_type == 'Corporate':
                filtered_counts['corporate'] += 1
                continue
            
            custom_keys = prop.get('CustomKeysData', {})
            status_2 = False
            if custom_keys:
                custom_key_list = custom_keys.get('CustomKeyData', [])
                if isinstance(custom_key_list, dict):
                    custom_key_list = [custom_key_list]
                
                for key_data in custom_key_list:
                    if key_data.get('Key') == 'PROPERTY_STATUS' and key_data.get('Value') == '2':
                        status_2 = True
                        break
            
            if status_2:
                filtered_counts['status_2'] += 1
                continue
            
            if not prop_name or prop_name.strip() == '':
                filtered_counts['no_name'] += 1
                continue
            
            if prop_name.startswith('z') or prop_name.startswith('Z'):
                filtered_counts['starts_z'] += 1
                continue
            
            if any(keyword in prop_name.lower() for keyword in exclude_keywords):
                filtered_counts['keyword'] += 1
                continue
            
            address = prop.get('Address', {})
            country = address.get('Country', '')
            if country == 'CAN':
                filtered_counts['canadian'] += 1
                continue
            
            # Check operational data
            has_operational_data = (
                prop.get('YearBuilt') or 
                prop.get('PropertyHours') or 
                prop.get('webSite') or
                prop.get('LongDescription') or
                prop.get('ShortDescription') or
                prop.get('LeaseTerms')
            )
            
            if not has_operational_data:
                filtered_counts['no_operational'] += 1
                if len(no_op_sample) < 5:
                    no_op_sample.append({
                        'id': prop_id,
                        'name': prop_name,
                        'type': prop_type,
                        'yearbuilt': prop.get('YearBuilt'),
                        'hours': bool(prop.get('PropertyHours')),
                        'website': bool(prop.get('webSite')),
                        'desc': bool(prop.get('LongDescription') or prop.get('ShortDescription')),
                        'terms': bool(prop.get('LeaseTerms'))
                    })
                continue
            
            filtered_counts['kept'] += 1
            if len(kept_sample) < 5:
                kept_sample.append({
                    'id': prop_id,
                    'name': prop_name,
                    'type': prop_type
                })
        
        print("Filtering Results:")
        print("-" * 80)
        print(f"❌ IsDisabled=1: {filtered_counts['disabled']}")
        print(f"❌ Type=Corporate: {filtered_counts['corporate']}")
        print(f"❌ PROPERTY_STATUS='2' (closed): {filtered_counts['status_2']}")
        print(f"❌ No name: {filtered_counts['no_name']}")
        print(f"❌ Starts with 'z' or 'Z': {filtered_counts['starts_z']}")
        print(f"❌ Contains excluded keyword: {filtered_counts['keyword']}")
        print(f"❌ Canadian properties: {filtered_counts['canadian']}")
        print(f"❌ No operational data: {filtered_counts['no_operational']}")
        print(f"✓ KEPT: {filtered_counts['kept']}")
        print("-" * 80)
        
        if no_op_sample:
            print(f"\nSample properties excluded for 'no operational data':")
            for prop in no_op_sample:
                print(f"  {prop['id']:12} {prop['name'][:40]:40} Type={prop['type']}")
                print(f"               YearBuilt={prop['yearbuilt']}, Hours={prop['hours']}, Website={prop['website']}, Desc={prop['desc']}, Terms={prop['terms']}")
        
        if kept_sample:
            print(f"\nSample properties KEPT:")
            for prop in kept_sample:
                print(f"  {prop['id']:12} {prop['name'][:40]:40} Type={prop['type']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_properties_with_debug()
