"""
Pending Lease Report Generator
Works with manual data input or CSV import when API access is pending
"""

import pandas as pd
from datetime import datetime
import json

def create_sample_data():
    """Create sample pending lease data based on your screenshot"""
    data = [
        {"Property ID": "1122956", "Property Name": "48 West", "Pending Lease Count": 500},
        {"Property ID": "100064263", "Property Name": "Block20", "Pending Lease Count": 500},
        {"Property ID": "1126176", "Property Name": "Cobalt Row", "Pending Lease Count": 500},
        {"Property ID": "100071403", "Property Name": "Cottages at Tucson", "Pending Lease Count": 500},
        {"Property ID": "100084540", "Property Name": "Hannah Townhomes & Lofts", "Pending Lease Count": 500},
    ]
    return pd.DataFrame(data)

def load_from_csv(filename: str) -> pd.DataFrame:
    """
    Load property and lease data from CSV
    Expected columns: Property ID, Property Name, Pending Lease Count
    """
    try:
        df = pd.read_csv(filename)
        required_cols = ['Property ID', 'Property Name', 'Pending Lease Count']
        
        if all(col in df.columns for col in required_cols):
            return df
        else:
            print(f"⚠️  CSV must have columns: {', '.join(required_cols)}")
            return pd.DataFrame()
    except FileNotFoundError:
        print(f"⚠️  File not found: {filename}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return pd.DataFrame()

def load_from_json(filename: str) -> pd.DataFrame:
    """
    Load property and lease data from JSON
    Expected format: [{Property ID, Property Name, Pending Lease Count}, ...]
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except FileNotFoundError:
        print(f"⚠️  File not found: {filename}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return pd.DataFrame()

def manual_input_data() -> pd.DataFrame:
    """Manually input property data"""
    print("Manual Data Entry Mode")
    print("=" * 80)
    print("Enter property data. Press Enter with empty Property ID to finish.")
    print()
    
    data = []
    while True:
        prop_id = input("Property ID (or Enter to finish): ").strip()
        if not prop_id:
            break
        
        prop_name = input("Property Name: ").strip()
        pending_count = input("Pending Lease Count: ").strip()
        
        try:
            data.append({
                "Property ID": prop_id,
                "Property Name": prop_name,
                "Pending Lease Count": int(pending_count)
            })
            print(f"  ✓ Added: {prop_name}\n")
        except ValueError:
            print("  ⚠️  Invalid count, skipping entry\n")
    
    return pd.DataFrame(data)

def generate_excel_report(df: pd.DataFrame, output_filename: str = None):
    """Generate formatted Excel report from dataframe"""
    if df.empty:
        print("❌ No data to export")
        return
    
    # Sort by pending lease count (descending)
    df = df.sort_values('Pending Lease Count', ascending=False).reset_index(drop=True)
    
    # Generate filename with timestamp
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"pending_leases_report_{timestamp}.xlsx"
    
    # Add totals row
    total_properties = len(df)
    total_pending = df['Pending Lease Count'].sum()
    
    totals_row = pd.DataFrame({
        'Property ID': [''],
        'Property Name': ['TOTAL'],
        'Pending Lease Count': [total_pending]
    })
    
    df_with_totals = pd.concat([df, totals_row], ignore_index=True)
    
    # Create Excel with formatting
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        df_with_totals.to_excel(writer, sheet_name='Pending Leases', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Pending Leases']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Format header row
        for cell in worksheet[1]:
            cell.font = cell.font.copy(bold=True)
        
        # Format totals row (last row) - make it bold
        last_row = len(df_with_totals) + 1  # +1 because of header
        for cell in worksheet[last_row]:
            cell.font = cell.font.copy(bold=True)
        
        # Add summary sheet
        summary_data = {
            'Metric': [
                'Total Properties',
                'Total Pending Leases',
                'Average Pending Leases per Property',
                'Properties with Pending Leases',
                'Max Pending Leases (Single Property)',
                'Report Generated'
            ],
            'Value': [
                len(df),
                df['Pending Lease Count'].sum(),
                f"{df['Pending Lease Count'].mean():.1f}",
                (df['Pending Lease Count'] > 0).sum(),
                df['Pending Lease Count'].max(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        summary_sheet = writer.sheets['Summary']
        for column in summary_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            summary_sheet.column_dimensions[column_letter].width = adjusted_width
        
        for cell in summary_sheet[1]:
            cell.font = cell.font.copy(bold=True)
    
    print(f"\n✓ Excel report generated: {output_filename}")
    return output_filename

def main():
    print("=" * 80)
    print("ENTRATA PENDING LEASE REPORT GENERATOR")
    print("=" * 80)
    print()
    print("Data Input Options:")
    print("  1 - Load from CSV file")
    print("  2 - Load from JSON file")
    print("  3 - Manual data entry")
    print("  4 - Use sample data (for testing)")
    print()
    
    choice = input("Select option (1-4): ").strip()
    
    df = pd.DataFrame()
    
    if choice == '1':
        filename = input("Enter CSV filename: ").strip()
        df = load_from_csv(filename)
    elif choice == '2':
        filename = input("Enter JSON filename: ").strip()
        df = load_from_json(filename)
    elif choice == '3':
        df = manual_input_data()
    elif choice == '4':
        print("Using sample data...")
        df = create_sample_data()
    else:
        print("❌ Invalid option")
        return
    
    if df.empty:
        print("❌ No data loaded")
        return
    
    # Display data
    print("\n" + "=" * 80)
    print("PENDING LEASE DATA")
    print("=" * 80)
    print(df.to_string(index=False))
    
    # Display summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Properties: {len(df)}")
    print(f"Total Pending Leases: {df['Pending Lease Count'].sum()}")
    print(f"Average Pending Leases per Property: {df['Pending Lease Count'].mean():.1f}")
    print(f"Properties with Pending Leases: {(df['Pending Lease Count'] > 0).sum()}")
    print(f"Max Pending Leases (Single Property): {df['Pending Lease Count'].max()}")
    
    # Generate Excel
    print("\n" + "=" * 80)
    generate_excel_report(df)
    
    print("\n" + "=" * 80)
    print("NOTE: Once Entrata API access is enabled (Error 420 resolved),")
    print("use 'entrata_pending_leases.py' for automatic data retrieval.")
    print("=" * 80)

if __name__ == "__main__":
    main()
