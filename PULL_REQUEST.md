# Fix: Translation on Task and Event cards not working (#49707)

## Description
This PR fixes issue #49707 where dates in Task and Event cards were not being localized according to the user's language settings in the CRM module.

## Changes Made
- Added JavaScript override for `frappe.datetime.global_date_format` in `erpnext/public/js/crm_datetime.js` to use localized date formatting based on `frappe.boot.lang` and system date format settings
- Integrated the override into `erpnext/public/js/erpnext.bundle.js` to ensure it's loaded with the application
- Added unit tests in `erpnext/crm/test_datetime_localization.py` to verify the setup

## Technical Details
The fix works by overriding the `frappe.datetime.global_date_format` function to use:
- User's language settings from `frappe.boot.lang`
- Date format preferences from `frappe.boot.sysdefaults.date_format`
- Time format preferences from `frappe.boot.sysdefaults.time_format`
- Proper timezone handling when available
- Fallback to original implementation if errors occur

The implementation prefers dayjs (used by Frappe v15) but falls back to moment.js if needed.

## Testing
1. Set your user language to a non-English language (e.g., German)
2. Navigate to a Lead or Opportunity form
3. Check the Task and Event cards in the "Open Activities" section
4. Verify that dates are displayed in the correct language format according to System Settings

## Related Issues
closes #49707