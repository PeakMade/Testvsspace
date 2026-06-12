# Entrata Pending Lease Report

Generate Excel reports showing pending lease counts across all properties in your portfolio.

## ⚡ Quick Start (Without API Access)

If you're getting API Error 420, use the manual data entry tool:

```powershell
python manual_pending_leases.py
```

Then choose option:
- **Option 1**: Load from CSV (edit `pending_leases_template.csv` with your data)
- **Option 3**: Manual entry (type in your data)
- **Option 4**: Sample data (for testing)

## 📋 Using CSV Import

1. Edit `pending_leases_template.csv` with your property data:
   - Column A: Property ID
   - Column B: Property Name  
   - Column C: Pending Lease Count

2. Run the manual tool:
```powershell
python manual_pending_leases.py
```

3. Select option 1 and enter: `pending_leases_template.csv`

## 🔌 API Setup (Once Access is Enabled)

### Current Status
- ⚠️ **Error 420**: Your Entrata account needs to accept the new API agreement
- Contact: **partner-integrations@entrata.com** or **apisupport@entrata.com**

### Once API Access is Enabled

1. Install required packages:
```powershell
pip install -r requirements.txt
```

2. Credentials are already configured in `entrata_pending_leases.py`:
   - Username: pbatson@peakmade-test-17291
   - Base URL: https://peakmade-test-17291.entrata.com/api/v1

3. Run the automated script:
```powershell
python entrata_pending_leases.py
```

## 📊 Output

Both scripts generate:
- **Excel file** with two sheets:
  - "Pending Leases" - Full property list sorted by pending count
  - "Summary" - Total counts and statistics
- **CSV file** - Raw data export

## 📖 Lease Status Codes

- **1** = Pending (application submitted, not yet approved)
- **2** = Approved
- **3** = Current
- **4** = Notice
- **5** = Move Out

## 🔧 Troubleshooting

### Error 420: API Agreement Required
Contact Entrata support to accept new API agreement. Use `manual_pending_leases.py` in the meantime.

### Error 106: Auth Type Required
Auth section missing from request (handled automatically in script).

### Error 104: Invalid Domain
Check base URL format and API endpoint structure.

## 📁 Files

- `entrata_pending_leases.py` - Automated API script (requires API access)
- `manual_pending_leases.py` - Manual data entry tool (works now)
- `pending_leases_template.csv` - CSV template for data import
- `test_entrata_connection.py` - Test API connectivity
- `requirements.txt` - Python dependencies
