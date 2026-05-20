## Summary
Fixes false `Reserved Batch Conflict` errors during Delivery Note / Sales Invoice submission.

## Problem
ERPNext was treating a batch as reserved if a `Stock Reservation Entry` existed with:
- `docstatus = 1` even when it was already fully delivered
- a different warehouse than the warehouse being shipped from

This caused stale reservations from older Sales Orders to block new Delivery Notes.

## Changes
- Ignore `Stock Reservation Entry` rows where `delivered_qty >= reserved_qty`
- Ignore `Serial and Batch Entry` rows where `delivered_qty >= qty`
- Ignore reservation conflicts for Delivery Note / Sales Invoice rows when the reservation is in a different warehouse

## Reproduction
Example failures observed:
- `SO2507-00003-2` batch `BKP-12-0362-24/0125-36577`
- `SO2507-00003-2` batch `BKP-12-0362-24/0125-46569`

Both had fully delivered reservation rows in `Warehouse1 - K` while the new Delivery Notes were shipping from `Warehouse2 - K`.

## Validation
- Static check: `python -m py_compile erpnext/controllers/stock_controller.py`
- Verified reservation rows showed `reserved_qty == delivered_qty`
