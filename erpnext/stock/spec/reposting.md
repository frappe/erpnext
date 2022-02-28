# Stock Reposting

Stock "reposting" is process of re-processing Stock Ledger Entry and GL Entries
in event of backdated stock transaction.

*Backdated stock transaction*: Any stock transaction for which some
item-warehouse combination has a future transactions.

## Why is this required?
Stock Ledger is stateful, it maintains queue, qty at any
point in time. So if you do a backdated transaction all future values change,
queues need to be re-evaluated etc. Watch Nabin and Rohit's conference
presentation for explanation: https://www.youtube.com/watch?v=mw3WAnekGIM

## How is this implemented?
Whenever backdated transaction is detected, instead of
fully processing it while submitting, the processing is queued using "Repost
Item Valuation" doctype. Every hour a scheduled job runs and processes this
queue (for up to maximum of 25 minutes)


## Queue implementation
- "Repost item valuation" (RIV) is automatically submitted from backdated transactions. (check stock_controller.py)
- Draft and cancelled RIV are ignored.
- Keep filter of "submitted" documents when doing anything with RIVs.
- The default status is "Queued".
- When background job runs, it picks the oldest pending reposts and changes the status to "In Progress" and when it finishes it
changes to "Completed"
- There are two more status: "Failed" when reposting failed and "Skipped" when reposting is deemed not necessary so it's skipped.
- technical detail: Entry point for whole process is "repost_entries" function in repost_item_valuation.py


## How to identify broken stock data:
There are 4 major reports for checking broken stock data:
- Incorrect balance qty after the transaction - to check if the running total of qty isn't correct.
- Incorrect stock value report - to check incorrect value books in accounts for stock transactions
- Incorrect serial no valuation -specific to serial nos
- Stock ledger invariant check - combined report for checking qty, running total, queue, balance value etc
