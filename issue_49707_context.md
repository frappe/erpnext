# Issue #49707 Context

## Issue Description
Translation on Task and Event cards not working - dates are not being localized according to the user's language settings.

## Key Details
- Type: Bug
- Difficulty: Easy to moderate
- Module: CRM
- Versions: 
  - ERPNext: v15.79.0 (HEAD)
  - Frappe Framework: v15.81.1 (HEAD)
- Installation method: FrappeCloud

## Problem Statement
UI is in German but dates are not in German. Date format should be pulled from System Settings.

## Affected Doctypes
- Lead
- Opportunity
- Possibly others

## Suggested Solution
Date format should be pulled from System Settings.

## Skills Needed
- Python
- Frappe framework knowledge
- Localization concepts

## Solution Implemented
The issue was fixed by overriding the `frappe.datetime.global_date_format` function to use localized date formatting based on the user's language settings.

### Files Modified:
1. `erpnext/public/js/crm_datetime.js` - New file that overrides the global_date_format function
2. `erpnext/public/js/erpnext.bundle.js` - Added import for the new datetime localization file

### Technical Details:
- The original `frappe.datetime.global_date_format` function was using hardcoded English formats
- The override uses `frappe.boot.lang` and `frappe.boot.sysdefaults.date_format` to determine the user's locale
- Moment.js locale functionality is used to format dates according to the user's language
- The fix affects all areas using `frappe.datetime.global_date_format`, including Task and Event cards in CRM

### Testing:
- Verified dates are now properly localized according to system settings
- Tested with German language settings to confirm dates appear in German format