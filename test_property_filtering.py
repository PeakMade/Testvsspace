"""
Test updated property filtering to verify vendors and closed properties are excluded
"""
from app import get_all_properties

print("="*80)
print("TESTING UPDATED PROPERTY FILTERING")
print("="*80)

properties = get_all_properties()

print(f"\n✓ Retrieved {len(properties)} properties after filtering\n")

# Check if our suspect properties are in the list
suspect_ids = [
    ('1122493', 'BVSHSSF PE MEMBER, LP'),
    ('100090963', 'College Crossing at National'),
    ('100090964', 'Greyhound Village'),
    ('100126326', 'Kenect Nashville'),
    ('100154189', 'Lakeshore Towers'),
    ('100168545', 'Olathe Commons'),
    ('100013335', 'Solaire Oxford'),
    ('1183571', 'The Manor'),
    ('100090965', 'University Lofts')
]

print("Checking suspect properties:")
print("-" * 80)

found_suspects = []
for suspect_id, suspect_name in suspect_ids:
    found = False
    for prop in properties:
        if str(prop.get('PropertyID')) == suspect_id:
            found = True
            found_suspects.append(suspect_name)
            break
    
    status = "❌ EXCLUDED (good!)" if not found else "⚠️ STILL PRESENT"
    print(f"{suspect_id:12} {suspect_name:35} {status}")

print()
if found_suspects:
    print(f"⚠️ WARNING: {len(found_suspects)} suspect properties still present:")
    for name in found_suspects:
        print(f"  - {name}")
else:
    print("✓ SUCCESS: All suspect properties have been filtered out!")

print("\n" + "="*80)
