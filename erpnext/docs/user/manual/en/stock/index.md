For most small business that deal in physical goods, a large part of their net
worth is invested in the stock in hand.

### Material Flow

There are three main types of entries:

  * Purchase Receipt: Items received from Suppliers against Purchase Orders.
  * Stock Entry: Items transferred from one Warehouse to another.
  * Delivery Note: Items shipped to Customers.

#### How does ERPNext track stock movement / levels?

Tracking stock is not just about adding and subtracting quantities. Some
complications arise when:

  * Back-dated (past) entries are made / edited: This affects future stock levels and may lead to negative stock.
  * Stock has to be valued based on First-in-First-out: ERPNext needs to maintain a sequence of all transactions to know the exact value of your Items.
  * Stock reports are required at any point in time in the past: You have to lookup what was the quantity / value your stock of Item X on date Y.

To manage this, ERPNext collects all inventory transactions in a table called
the Stock Ledger Entry. All Purchase Receipts, Stock Entries and Delivery
Notes update this table.

### Topics

{index}
