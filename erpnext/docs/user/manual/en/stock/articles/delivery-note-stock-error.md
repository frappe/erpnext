# Delivery Note Negative Stock Error

**Question**: When submitting a Delivery Note, receiving a message says that item's stock is insufficient, but we have item's stock available in the Warehouse.

**Answer**: On submission of Delivery Note, stock level is checked as on Posting Date and Posting Time of a Delivery Note. It's possible that you have stock of an Item available in the Warehouse. But if you are creating back-dated Delivery Note, and if item was not available in the warehouse on the Posting Date and Posting Time of Delivery Note, you are likely to receive an error message on the negative stock. You can refer to the Stock Ledger report to confirm the same.

If this is the case, you should edit the Posting Date and Time of a Delivery Note, and ensure that it is after the Posting Date and Time of item's receipt entry.