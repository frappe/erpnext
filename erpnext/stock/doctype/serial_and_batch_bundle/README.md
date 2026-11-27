A Serial and Batch Bundle holds the serial numbers and batches that one voucher row moves in or out of a warehouse.

## Where the code is

| Path | What it does |
| --- | --- |
| `serial_and_batch_bundle.py` | The DocType: lifecycle hooks, totals, and the methods that other doctypes call. |
| `services/validation.py` | Checks the entries, the voucher link and the stock of the serial numbers. |
| `services/valuation.py` | Sets the incoming rate of inward and outward bundles. |
| `services/returns.py` | Sets the rate of return bundles and checks them against the original voucher. |
| `services/batch_stock.py` | Stops negative batch stock. |
| `services/future_transactions.py` | Stops backdated entries when later entries use the same serial numbers or batches. |
| `services/voucher_link.py` | Links the bundle to its voucher row and removes the link. |
| `api.py`, `csv_import.py`, `inline_editor.py` | Whitelisted methods for the selector dialog, the CSV import and the inline editor. |
| `erpnext/stock/serial_batch_bundle/` | The engine: bundle creation, Stock Ledger Entry posting, serial and batch valuation, and bundle entry reads. |
| `erpnext/stock/serial_batch_bundle/availability/` | Available serial numbers and batches, with POS, Stock Reservation Entry and Pick List reservations. |
| `erpnext/stock/services/serial_batch_*_service.py` | Bundles and checks for the rows of a stock voucher. |

A service takes the bundle document: `BundleValuation(bundle).set_incoming_rate_for_inward_transaction(row)`. Other doctypes call the bundle methods, for example `bundle.set_incoming_rate()`. The old import paths of `serial_and_batch_bundle.py` stay available for other apps and for whitelisted method paths.
