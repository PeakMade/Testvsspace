from app import get_all_properties

props = get_all_properties()
print(f'Total properties: {len(props)}\n')

# Check for problematic properties
problematic = []
for p in props:
    name = p.get('MarketingName', '').lower()
    if any(keyword in name for keyword in ['connect', 'redpoint', 'retail', 'corporate', 'shuttle']):
        problematic.append(f"{p.get('PropertyID')} - {p.get('MarketingName')}")

if problematic:
    print("❌ Found problematic properties:")
    for prop in problematic:
        print(f"  {prop}")
else:
    print("✓ No problematic properties found")

# Show last 10 properties
print("\nLast 10 properties in list:")
for p in props[-10:]:
    print(f"  {p.get('PropertyID')} - {p.get('MarketingName')}")
