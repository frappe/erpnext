# Implementation notes for Stock Ledger


## Important files

- `stock/stock_ledger.py`
- `controllers/stock_controller.py`
- `stock/valuation.py`

## What is in an Stock Ledger Entry (SLE)?

Stock Ledger Entry is a single row in the Stock Ledger. It signifies some
modification of stock for a particular Item in the specified warehouse.

- `item_code`: item for which ledger entry is made
- `warehouse`: warehouse where inventory is affected
- `actual_qty`: change in qty
- `qty_after_transaction`: quantity available after the transaction is processed
- `incoming_rate`: rate at which inventory was received.
- `is_cancelled`: if 1 then stock ledger entry is cancelled and should not be used
for any business logic except for the code that handles cancellation.
- `posting_date` & `posting_time`: Specify the temporal ordering of stock ledger
  entries. Ties are broken by `creation` timestamp.
- `voucher_type`: Many transaction can create SLE, e.g. Stock Entry, Purchase
  Invoice
- `voucher_no`: `name` of the transaction that created SLE
- `voucher_detail_no`: `name` of the child table row from parent transaction
  that created the SLE.
- `dependant_sle_voucher_detail_no`: cross-warehouse transfers need this
  reference in order to update dependent warehouse rates in case of change in
  rate.
- `recalculate_rate`: if this is checked in/out rates are recomputed on
  transactions.
- `valuation_rate`: current average valuation rate.
- `stock_value`: current total stock value
- `stock_value_difference`: stock value difference made between last and current
  entry. This value is booked in accounting ledger.
- `stock_queue`: if FIFO/LIFO is used this represents queue/stack maintained for
  computing incoming rate for inventory getting consumed.
- `batch_no`: batch no for which stock entry is made; each stock entry can only
  affect one batch number.
- `serial_no`: newline separated list of serial numbers that were added (if
  actual_qty > 0) or else removed. Currently multiple serial nos can have single
  SLE but this will likely change in future.


## Implementation of Stock Ledger

Stock Ledger Entry affects stock of combinations of (item_code, warehouse) and
optionally batch no if specified. For simplicity, lets avoid batch no. for now.


Stock Ledger Entry table stores stock ledger for all combinations of item_code
and warehouse. So whenever any operations are to be performed on said
item-warehouse combination stock ledger is filtered and sorted by posting
datetime. A typical query that will give you individual ledger looks like this:

```sql
select *
from `tabStock Ledger Entry` as sle
where
    is_cancelled = 0  --- cancelled entries don't affect ledger
    and item_code = 'item_code' and warehouse = 'warehouse_name'
order by timestamp(posting_date, posting_time), creation
```

New entry is just an update to the last entry which is found by looking at last
row in the filter ledger.


### Serial nos

Serial numbers do not follow any valuation method configuration and they are
consumed at rate they were produced unless they are grouped in which case they
are consumed at weighted average rate.


### Batch Nos

Batches are currently NOT consumed as per batch wise valuation rate, instead
global FIFO queue for the item is used for valuation rate.


## Creation process of SLEs

- SLE creation is usually triggered by Stock Transactions using a method
  conventionally named `update_stock_ledger()` This might not be defined for
  stock transaction and could be specified somewhere in inheritance hierarchy of
  controllers.
- This method produces SLE objects which are processed by `make_sl_entries` in
  `stock_ledger.py` which commits the SLE to database.
- `update_entries_after` class is used to process ONLY the inserted SLE's queue
  and valuation.
- The change in qty is propagated to future entries immediately. Valuation and
  queue for future entries is processed in background using repost item
  valuation.


## Accounting impact

- Accounting impact for stock transaction is handled by `get_gl_entries()`
  method on controllers. Each transaction has different business logic for
  booking the accounting impact.
