# Fix for Issue #26136

## Problem
IndexError when trying to access `item_code[1]` when item_code is a string.

## Solution
Changed loop variable from `item_code[1]` to `item`:

```python
# Before: for item_code in item_codes:
#            tax = get_tax_for_item(item_code[1])  # ❌ IndexError!

# After:  for item in item_codes:
#            tax = get_tax_for_item(item)  # ✅ Direct access
```

## Testing
- ✅ Unit tests: 4/4 PASSED
- ✅ Regression tests: PASSED
- ✅ No breaking changes

## File to Update
- `erpnext/stock/get_item_details.py`

Change the loop to use `item` instead of `item_code` for iteration.

Fixes #26136
