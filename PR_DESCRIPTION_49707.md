# Fix: Translation on Task and Event cards not working (#49707)

## Issue Description
Fixes #49707 - Translation on Task and Event cards not working. Dates are not being localized according to the user's language settings in the CRM module.

## Root Cause
The issue was in the `frappe.datetime.global_date_format` function which was using hardcoded English date formats regardless of the user's language settings. This affected Task and Event cards in the CRM module for Lead and Opportunity doctypes.

## Solution
1. **JavaScript Override**: Created a JavaScript file that overrides the `frappe.datetime.global_date_format` function to use the user's locale settings from `frappe.boot.lang` and `frappe.boot.sysdefaults.date_format`.

2. **Bundle Integration**: Added the new JavaScript file to the `erpnext.bundle.js` to ensure it's loaded with the application.

## Changes Made
- Added `erpnext/public/js/crm_datetime.js` - Overrides the global_date_format function to use localized formatting
- Modified `erpnext/public/js/erpnext.bundle.js` - Added import for the new datetime localization file
- Added `erpnext/crm/test_datetime_localization.py` - Unit tests for the localization functionality

## Testing
- Verified that dates are now properly localized according to system settings
- Tested with German language settings to confirm dates appear in German format
- Added unit tests to ensure the localization function works correctly

## Affected Areas
- Task and Event cards in CRM for Lead and Opportunity doctypes
- Any other areas using `frappe.datetime.global_date_format` in the ERPNext application

## How to Test
1. Set your user language to a non-English language (e.g., German)
2. Navigate to a Lead or Opportunity form
3. Check the Task and Event cards in the "Open Activities" section
4. Verify that dates are displayed in the correct language format

## Screenshots (if applicable)
Before fix: Dates shown in English format regardless of user language
After fix: Dates shown in user's selected language format

## Additional Notes
This fix ensures that all date formatting in the CRM module respects the user's language preferences as set in System Settings, providing a consistent localized experience.