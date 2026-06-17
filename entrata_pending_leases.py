"""
Entrata API - Lease Report by Status
Retrieves lease counts by status (Pending, Denied, Approved, Current, Notice, Past, Cancelled) for all properties
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta, date as date_type
from typing import Dict, List, Optional, Set
import time
import os
import glob
from dotenv import load_dotenv

class EntrataAPI:
    def __init__(self, api_key: str, org: str, debug: bool = False):
        """
        Initialize Entrata API client
        
        Args:
            api_key: Entrata API key
            org: Organization name (e.g., 'peakmade')
            debug: Enable verbose debugging output
        """
        self.api_key = api_key
        self.org = org
        self.base_url = f"https://apis.entrata.com/ext/orgs/{org}/v1"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Api-Key': api_key
        }
        self.request_count = 0
        self.properties_endpoint = f"{self.base_url}/properties"
        self.leases_endpoint = f"{self.base_url}/leases"
        self.debug = debug
        self.bisection_count = 0
    
    def _build_request(self, method: str, params: Dict = None, version: str = "r2") -> Dict:
        """Build Entrata API request payload"""
        request_payload = {
            "auth": {
                "type": "apikey"
            },
            "requestId": str(int(datetime.now().timestamp() * 1000)),
            "method": {
                "name": method,
                "version": version,
                "params": params or {}
            }
        }
        return request_payload
    
    def _make_request(self, endpoint_url: str, payload: Dict, retry_count: int = 3) -> Dict:
        """Make API request to Entrata with retry logic"""
        self.request_count += 1
        
        for attempt in range(retry_count):
            try:
                response = requests.post(
                    endpoint_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                # Check response status
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check for API-level errors
                    if 'response' in result:
                        resp_data = result['response']
                        if 'error' in resp_data:
                            error = resp_data['error']
                            error_code = error.get('code')
                            error_msg = error.get('message', 'Unknown error')
                            print(f"  ⚠️  API Error {error_code}: {error_msg}")
                            return None
                        elif 'code' in resp_data and resp_data['code'] != 200:
                            error_msg = resp_data.get('message', 'Unknown error')
                            print(f"  ⚠️  API Error: {error_msg}")
                            return None
                    
                    return result
                else:
                    print(f"  ⚠️  HTTP {response.status_code}: {response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                print(f"  ⚠️  Request timeout (attempt {attempt + 1}/{retry_count})")
                if attempt < retry_count - 1:
                    time.sleep(2)
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  Request failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
        
        return None
    
    def get_properties(self, save_to_file: str = None, exclude_states: List[str] = None, exclude_countries: List[str] = None) -> List[Dict]:
        """
        Get all properties with optional filtering
        
        Args:
            save_to_file: If provided, save properties to this JSON file
            exclude_states: List of state codes to exclude (e.g., ['CA', 'TX'])
            exclude_countries: List of country codes to exclude (e.g., ['CA', 'MX'])
        """
        print("Fetching properties from Entrata API...")
        payload = self._build_request("getProperties", version="r1")
        result = self._make_request(self.properties_endpoint, payload)
        
        exclude_states = exclude_states or []
        exclude_countries = exclude_countries or []
        exclude_keywords = ['retail', 'reit', 'llc', 'corporate', 'shuttle', 'condominium', 'assoc', 'master', 'ucc', 'university center', 'gateway']
        
        properties = []
        if result and 'response' in result:
            response_data = result['response']
            
            # Handle different response structures
            if 'result' in response_data:
                result_data = response_data['result']
                # Try multiple structure variations
                if 'PhysicalProperty' in result_data:
                    phys_prop = result_data['PhysicalProperty']
                    properties = phys_prop.get('Property', [])
                elif 'Properties' in result_data:
                    properties = result_data['Properties'].get('Property', [])
                elif 'Property' in result_data:
                    properties = result_data['Property']
            elif 'Property' in response_data:
                properties = response_data['Property']
            elif 'PhysicalProperty' in response_data:
                phys_prop = response_data['PhysicalProperty']
                properties = phys_prop.get('Property', [])
            
            # Ensure it's a list
            if isinstance(properties, dict):
                properties = [properties]
        
        # Filter out excluded keywords (retail, UCC, etc.)
        if exclude_keywords:
            original_count = len(properties)
            filtered = []
            for prop in properties:
                prop_name = prop.get('MarketingName', '') or prop.get('PropertyName', '') or ''
                
                # Skip if name contains excluded keywords
                if any(keyword in prop_name.lower() for keyword in exclude_keywords):
                    print(f"  Excluding {prop_name} (matches keyword filter)")
                    continue
                
                filtered.append(prop)
            
            properties = filtered
            if len(properties) < original_count:
                print(f"✓ Filtered {original_count} → {len(properties)} properties (removed keyword matches)")
        
        # Filter out properties starting with 'z' or 'Z'
        original_count = len(properties)
        filtered = []
        for prop in properties:
            prop_name = prop.get('MarketingName', '') or prop.get('PropertyName', '') or ''
            
            # Skip if name starts with 'z' or 'Z'
            if prop_name.startswith('z') or prop_name.startswith('Z'):
                print(f"  Excluding {prop_name} (starts with 'z' or 'Z')")
                continue
            
            filtered.append(prop)
        
        properties = filtered
        if len(properties) < original_count:
            print(f"✓ Filtered {original_count} → {len(properties)} properties (removed 'z'/'Z' prefix properties)")
        
        # Filter out excluded states/countries
        if exclude_states or exclude_countries:
            original_count = len(properties)
            filtered = []
            for prop in properties:
                # Check various address structures
                address = prop.get('Address', {})
                addresses = prop.get('Addresses', {}).get('Address', [])
                if isinstance(addresses, dict):
                    addresses = [addresses]
                
                state = address.get('State') or address.get('StateCode')
                country = address.get('Country')
                
                # Also check in Addresses array
                if not state and addresses:
                    state = addresses[0].get('StateCode') or addresses[0].get('State')
                if not country and addresses:
                    country = addresses[0].get('Country')
                
                # Exclude if matches
                if state in exclude_states:
                    print(f"  Excluding {prop.get('MarketingName', 'Unknown')} (State: {state})")
                    continue
                if country in exclude_countries:
                    print(f"  Excluding {prop.get('MarketingName', 'Unknown')} (Country: {country})")
                    continue
                
                filtered.append(prop)
            
            properties = filtered
            print(f"✓ Filtered {original_count} → {len(properties)} properties")
        
        if save_to_file and properties:
            with open(save_to_file, 'w') as f:
                json.dump(properties, f, indent=2)
            print(f"✓ Saved {len(properties)} properties to {save_to_file}")
        
        return properties
    
    def get_leases(self, property_id: str = None, lease_status: int = None, academic_year: int = None) -> List[Dict]:
        """
        Get leases with optional filters using native API pagination
        
        Args:
            property_id: Filter by property ID
            lease_status: Filter by lease status (1 = Pending)
            academic_year: Academic year start (e.g., 2025 for 2025-2026). If None, uses current/upcoming year.
        """
        
        def _extract(result_data: Dict) -> List[Dict]:
            leases: List[Dict] = []
            if 'leases' in result_data:
                ld = result_data['leases']
                leases = ld.get('lease', []) if isinstance(ld, dict) else ld
            elif 'Leases' in result_data:
                ld = result_data['Leases']
                leases = ld.get('Lease', []) if isinstance(ld, dict) else ld
            elif 'lease' in result_data:
                leases = result_data['lease']
            elif 'Lease' in result_data:
                leases = result_data['Lease']
            if isinstance(leases, dict):
                leases = [leases]
            return leases or []

        # Determine academic year date range
        if academic_year is None:
            today = date_type.today()
            current_year = today.year
            current_month = today.month
            
            # Determine academic year: if we're before August, use current year; otherwise next year
            if current_month >= 8:  # August or later
                academic_year_start = current_year
            else:  # Before August
                academic_year_start = current_year
        else:
            academic_year_start = academic_year
        
        start_date = date_type(academic_year_start, 8, 1)  # August 1
        end_date = date_type(academic_year_start + 1, 7, 31)  # July 31 next year
        
        if self.debug:
            print(f"  📅 Querying academic year {academic_year_start}-{academic_year_start + 1}: {start_date} to {end_date}")
        
        # Build base parameters
        params: Dict = {}
        if property_id:
            params['propertyId'] = str(property_id)
        if lease_status is not None:
            params['leaseStatusTypeIds'] = str(lease_status)
        params['moveInDateFrom'] = start_date.strftime('%m/%d/%Y')
        params['moveInDateTo'] = end_date.strftime('%m/%d/%Y')
        
        # Use native pagination with page_no and per_page
        all_leases = []
        page_no = 1
        per_page = 500
        
        while True:
            params['page_no'] = page_no
            params['per_page'] = per_page
            
            if self.debug:
                print(f"    📄 Fetching page {page_no} (per_page={per_page})")
            
            raw = self._make_request(self.leases_endpoint, self._build_request('getLeases', params))
            if not raw or 'response' not in raw:
                break
            
            rd = raw['response']
            result_data = rd.get('result', rd)
            leases = _extract(result_data)
            
            if self.debug:
                print(f"    ✓ Returned {len(leases)} records (total: {len(all_leases) + len(leases)})")
            
            if not leases or len(leases) == 0:
                # No more leases, we're done
                break
            
            all_leases.extend(leases)
            
            # If we got fewer than per_page, we've reached the end
            if len(leases) < per_page:
                if self.debug:
                    print(f"    ✅ Got {len(leases)} < {per_page} - reached end")
                break
            
            # Move to next page
            page_no += 1
            
            # Safety check to prevent infinite loops
            if page_no > 50:
                print(f"  ⚠️  Safety limit: stopped after 50 pages (25,000 records)")
                break
        
        return all_leases
    
    def get_lease_counts_by_status(self, properties: List[Dict] = None, academic_year: int = None) -> pd.DataFrame:
        """
        Get lease counts by status for all properties
        Returns a DataFrame with Property ID, Property Name, and counts for each status
        
        Args:
            properties: Optional list of properties. If not provided, will fetch from API.
            academic_year: Academic year start (e.g., 2025 for 2025-2026). If None, uses current/upcoming year.
        """
        if properties is None:
            properties = self.get_properties(save_to_file="properties.json")
        
        if not properties:
            print("❌ No properties found or API error occurred")
            return pd.DataFrame()
        
        # Status types
        statuses = {
            1: 'Pending',
            2: 'Denied',
            3: 'Approved',
            4: 'Current',
            5: 'Notice',
            6: 'Past',
            7: 'Cancelled'
        }
        
        print(f"✓ Found {len(properties)} properties")
        print("\n" + "="*80)
        print("Fetching leases for each property by status...")
        print("="*80)
        
        results = []
        errors = []
        
        for idx, prop in enumerate(properties, 1):
            # Try multiple field name variations for property ID and name
            property_id = (prop.get('PropertyID') or prop.get('PropertyId') or 
                          prop.get('propertyId') or prop.get('property_id') or prop.get('id') or
                          prop.get('Id'))
            property_name = (prop.get('MarketingName') or prop.get('PropertyName') or 
                           prop.get('propertyName') or prop.get('property_name') or 
                           prop.get('name') or prop.get('PropertyLookupCode') or 'Unknown')
            
            if not property_id:
                print(f"[{idx}/{len(properties)}] ⚠️  Skipping property (no ID found): {prop}")
                continue
            
            print(f"\n[{idx}/{len(properties)}] Processing: {property_name} (ID: {property_id})")
            
            try:
                row_data = {
                    'Property ID': str(property_id),
                    'Property Name': property_name
                }
                
                # Get leases for each status
                total = 0
                for status_id, status_name in statuses.items():
                    leases = self.get_leases(property_id=str(property_id), lease_status=status_id, academic_year=academic_year)
                    count = len(leases) if leases else 0
                    row_data[status_name] = count
                    total += count
                    print(f"  ✓ {status_name}: {count}")
                
                row_data['Total'] = total
                results.append(row_data)
                
                print(f"  ✓ Total: {total} lease(s)")
                
            except Exception as e:
                error_msg = f"Error processing {property_name} (ID: {property_id}): {str(e)}"
                print(f"  ❌ {error_msg}")
                errors.append(error_msg)
                
                # Add property with error marker
                row_data = {
                    'Property ID': str(property_id),
                    'Property Name': property_name
                }
                for status_name in statuses.values():
                    row_data[status_name] = -1  # -1 indicates error
                row_data['Total'] = -1
                results.append(row_data)
            
            # Small delay to avoid rate limiting
            time.sleep(0.25)
        
        # Create DataFrame and sort by total count (descending - highest to lowest)
        df = pd.DataFrame(results)
        if not df.empty and 'Total' in df.columns:
            df = df.sort_values('Total', ascending=False)
        
        # Report errors
        if errors:
            print("\n" + "="*80)
            print(f"⚠️  ERRORS ENCOUNTERED ({len(errors)}):")
            print("="*80)
            for error in errors:
                print(f"  - {error}")
        
        return df


def cleanup_old_reports(pattern: str, keep_count: int = 1):
    """Delete old report files, keeping only the most recent ones.
    
    Args:
        pattern: File pattern to match (e.g., 'entrata_pending_leases_*.xlsx')
        keep_count: Number of most recent files to keep (default: 1)
    """
    files = glob.glob(pattern)
    if len(files) <= keep_count:
        return
    
    # Sort by modification time, newest first
    files_with_time = [(f, os.path.getmtime(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # Delete old files
    files_to_delete = [f[0] for f in files_with_time[keep_count:]]
    if files_to_delete:
        print(f"\n🗑️  Cleaning up {len(files_to_delete)} old report(s)...")
        for file in files_to_delete:
            try:
                os.remove(file)
                print(f"  Deleted: {os.path.basename(file)}")
            except Exception as e:
                print(f"  ⚠️  Could not delete {os.path.basename(file)}: {e}")


def main():
    """Main execution"""
    print("=" * 80)
    print("ENTRATA PENDING LEASE REPORT")
    print("=" * 80)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    ENTRATA_API_KEY = os.getenv('ENTRATA_API_KEY')
    ENTRATA_ORG = os.getenv('ENTRATA_ORG', 'peakmade')
    
    if not ENTRATA_API_KEY:
        print("❌ Error: ENTRATA_API_KEY not found in .env file")
        print("Please add your production API key to the .env file:")
        print("   ENTRATA_API_KEY=your_api_key_here")
        return
    
    print(f"Using organization: {ENTRATA_ORG}")
    print(f"API Key: {ENTRATA_API_KEY[:8]}...{ENTRATA_API_KEY[-4:]}" if len(ENTRATA_API_KEY) > 12 else "API Key: [SET]")
    print()
    
    # Initialize API client (set debug=True to see detailed pagination info)
    api = EntrataAPI(ENTRATA_API_KEY, ENTRATA_ORG, debug=False)
    
    # Step 1: Get and save properties (excluding Canadian properties)
    # To exclude Canada, use: exclude_countries=['CAN'] (using 3-letter code to avoid confusion with CA state)
    # To exclude California state, use: exclude_states=['CA']
    properties = api.get_properties(save_to_file="properties.json", exclude_countries=['CAN'])
    
    if not properties:
        print("\n❌ No properties retrieved. Please check your API credentials and connection.")
        return
    
    # Step 2: Generate report for 2026-2027 academic year
    year = 2025  # 2026-2027
    
    print("\n" + "=" * 80)
    print(f"GENERATING REPORT FOR ACADEMIC YEAR {year}-{year+1}")
    print("=" * 80)
    
    df = api.get_lease_counts_by_status(properties=properties, academic_year=year)
    
    if df.empty:
        print(f"\n❌ No data retrieved for {year}-{year+1}.")
        return
    
    # Filter out errors (-1 values) for summary
    df_valid = df[df['Total'] >= 0].copy()
    df_errors = df[df['Total'] < 0].copy()
    
    # Filter out status columns where all values are 0 (not relevant for this year)
    all_status_columns = ['Pending', 'Denied', 'Approved', 'Current', 'Notice', 'Past', 'Cancelled']
    status_columns_to_keep = []
    status_columns_removed = []
    
    for status in all_status_columns:
        if status in df_valid.columns:
            # Check if any property has non-zero value for this status
            if df_valid[status].sum() > 0:
                status_columns_to_keep.append(status)
            else:
                status_columns_removed.append(status)
    
    if status_columns_removed:
        print(f"\n📊 Filtering out zero-only columns: {', '.join(status_columns_removed)}")
        print(f"✓ Keeping columns with data: {', '.join(status_columns_to_keep)}")
    
    # Keep only columns with data + Property ID, Property Name, Total
    columns_to_keep = ['Property ID', 'Property Name'] + status_columns_to_keep + ['Total']
    df_valid = df_valid[columns_to_keep]
    
    # Recalculate Total based on remaining status columns only
    for idx in df_valid.index:
        row_total = sum(df_valid.loc[idx, status] for status in status_columns_to_keep if status in df_valid.columns)
        df_valid.loc[idx, 'Total'] = row_total
    
    # Update status_columns to only include kept columns for rest of script
    status_columns = status_columns_to_keep
    
    # Sort by total lease count (descending)
    df_valid = df_valid.sort_values('Total', ascending=False)
    
    # Display results
    print("\n" + "=" * 80)
    print(f"RESULTS - LEASE COUNTS BY STATUS ({year}-{year+1})")
    print("=" * 80)
    print(df_valid.to_string(index=False))
    
    if not df_errors.empty:
        print("\n" + "=" * 80)
        print(f"⚠️  PROPERTIES WITH ERRORS ({len(df_errors)}):")
        print("=" * 80)
        print(df_errors[['Property ID', 'Property Name']].to_string(index=False))
    
    # Summary statistics
    print("\n" + "=" * 80)
    print(f"SUMMARY ({year}-{year+1})")
    print("=" * 80)
    print(f"Total Properties Processed: {len(df)}")
    print(f"Properties Successfully Queried: {len(df_valid)}")
    if not df_errors.empty:
        print(f"Properties with Errors: {len(df_errors)}")
    
    # Status-specific summaries
    print("\nLeases by Status:")
    for status in status_columns:
        if status in df_valid.columns:
            total = df_valid[status].sum()
            print(f"  {status}: {total}")
    
    print(f"\nTotal Leases (All Statuses): {df_valid['Total'].sum()}")
    print(f"Average Leases per Property: {df_valid['Total'].mean():.1f}")
    print(f"Properties with Leases: {(df_valid['Total'] > 0).sum()}")
    print(f"Max Leases (Single Property): {df_valid['Total'].max()}")
    
    # Export to Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"entrata_lease_report_{year}_{year+1}_{timestamp}.xlsx"
    csv_file = f"entrata_lease_report_{year}_{year+1}_{timestamp}.csv"
    
    # Clean up old reports for this year before saving new ones
    cleanup_old_reports(f"entrata_lease_report_{year}_{year+1}_*.xlsx", keep_count=1)
    cleanup_old_reports(f"entrata_lease_report_{year}_{year+1}_*.csv", keep_count=1)
    
    # Add totals row to valid data (using only kept status columns)
    totals_row_data = {
        'Property ID': [''],
        'Property Name': ['TOTAL']
    }
    for status in status_columns:
        if status in df_valid.columns:
            totals_row_data[status] = [df_valid[status].sum()]
    totals_row_data['Total'] = [df_valid['Total'].sum()]
    
    totals_row = pd.DataFrame(totals_row_data)
    df_valid_with_totals = pd.concat([df_valid, totals_row], ignore_index=True)
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df_valid_with_totals.to_excel(writer, sheet_name='Lease Counts', index=False)
        
        # Format the totals row
        worksheet = writer.sheets['Lease Counts']
        last_row = len(df_valid_with_totals) + 1  # +1 for header
        for cell in worksheet[last_row]:
            cell.font = cell.font.copy(bold=True)
        
        if not df_errors.empty:
            df_errors.to_excel(writer, sheet_name='Errors', index=False)
    
    print(f"\n✓ Report exported to: {excel_file}")
    
    # Also save as CSV (with totals)
    df_valid_with_totals.to_csv(csv_file, index=False)
    print(f"✓ Report exported to: {csv_file}")
    
    print(f"\n✓ Total API requests made: {api.request_count}")


if __name__ == "__main__":
    main()
