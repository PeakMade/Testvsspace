from entrata_pending_leases import EntrataAPI
import os
from dotenv import load_dotenv

load_dotenv()
ENTRATA_API_KEY = os.getenv('ENTRATA_API_KEY')
ENTRATA_ORG = os.getenv('ENTRATA_ORG', 'peakmade')

api = EntrataAPI(ENTRATA_API_KEY, ENTRATA_ORG)
print('Fetching all properties (no filters)...')
props = api.get_properties(exclude_states=[], exclude_countries=[])

# Check for Canadian properties
canadian = []
for p in props:
    country = p.get('PhysicalAddress', {}).get('Country', '').upper()
    if country in ['CA', 'CAN', 'CANADA']:
        canadian.append(p)

print(f'\nFound {len(canadian)} Canadian properties:')
for p in canadian:
    country = p.get('PhysicalAddress', {}).get('Country')
    name = p.get('MarketingName')
    prop_id = p.get('PropertyId')
    print(f"  - {name} (ID: {prop_id}, Country: {country})")

if not canadian:
    print('  (None found - all Canadian properties may have been filtered by other criteria)')
