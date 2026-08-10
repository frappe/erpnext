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
Item Valuation" doctype. Two scheduled modes exist, selected by "Stock
Reposting Settings > Enable Parallel Reposting":

- *Parallel reposting enabled*: a cron job runs every 15 minutes as a recovery
  net; each reposting job also re-triggers the dispatcher on completion, so the
  queue drains continuously between cron ticks. Up to "No of Parallel
  Reposting" entries (default 4) run concurrently, at most one per item.
- *Parallel reposting disabled*: an hourly maintenance job processes the queue
  sequentially.

Both modes respect the reposting timeslot configured in Stock Reposting
Settings. There is no fixed per-run time budget.


## Queue implementation
- "Repost item valuation" (RIV) is automatically submitted from backdated transactions. (check stock_controller.py)
- Draft and cancelled RIV are ignored.
- Keep filter of "submitted" documents when doing anything with RIVs.
- The default status is "Queued".
- When background job runs, it picks the oldest pending reposts and changes the status to "In Progress" and when it finishes it
changes to "Completed"
- There are two more status: "Failed" when reposting failed and "Skipped" when reposting is deemed not necessary so it's skipped.
- technical detail: entry points are "run_parallel_reposting" (parallel mode,
  15-minute cron) and "repost_entries" (sequential mode, hourly) in
  repost_item_valuation.py


## How to identify broken stock data:
There are 4 major reports for checking broken stock data:
- Incorrect balance qty after the transaction - to check if the running total of qty isn't correct.
- Incorrect stock value report - to check incorrect value books in accounts for stock transactions
- Incorrect serial no valuation -specific to serial nos
- Stock ledger invariant check - combined report for checking qty, running total, queue, balance value etc
