---
{
	"_label": "Accounting of Inventory / Stock"
}
---

The value of available inventory is treated as an Asset in company's Chart of Accounts. Depending on the type of item, it can be treated as Fixed Asset or Current Asset. To prepare Balance Sheet, you should make the accounting entry for those assets. 
There are generally two different methods of accounting for inventory:


## **Periodic Accounting**

In this method, the system does not create accounting entries automatically for assets, at the time of material puchases or sales.

In an accounting period, you buy and receive items of a certain value. This value is marked as an expense in your accounting books. You sell and deliver some of these items. 

At the end of an accounting period, the total value of items, that remain to be sold, need to be booked as the company’s assets, often known as stock-in-hand. 

The difference between the value of the items remaining to be sold and the previous period’s stock-in-hand can be positive or negative. If positive, this value is removed from expenses (cost-of-goods-sold) and is added to assets (stock-in-hand / fixed-assets). If negative, a reverse entry is passed. 

This complete process is called Periodic Accounting. 

This process is usually followed when using a manual system of book keeping. It reduces effort at the cost of accuracy.

-

## **Auto / Perpetual Accounting**

When you buy and receive items, those items are booked as the company’s assets (stock-in-hand / fixed-assets). When you sell and deliver those items, an expense (cost-of-goods-sold) equal to the buying cost of the items is booked. General Ledger entries are made after every transaction. This improves accuracy of Balance Sheet and Profit and Loss statement. And the value as per Stock Ledger always remains same with the relevant account balance. 

This process is called Perpetual Accounting.

-

### **Steps To Take Before Activation**

1. Setup the following default accounts for each Company 
	- Stock Received But Not Billed
	- Stock Adjustment Account
	- Expenses Included In Valuation
	- Cost Center
1. Enter Asset / Expense account for each warehouse depending upon type of warehouse (Stores, Fixed Asset Warehouse etc).

>Note: If you are currently using Periodic Accounting and want to switch to Auto / Perpetual Accounting, follow the steps below:
>
>- Follow Step 1
>- To enable Perpetual Accounting, existing stock balances must be synced with relevant account balances. To do that, calculate available stock value and book stock-in-hand/fixed-asset (asset) against cost-of-goods-sold (expense) through Journal Voucher.
>- Create new warehouse for every existing warehouse.
>-  Assign Asset / Expense account while creating warehouse.
>-  Create Stock Entry (Material Transfer) to transfer available stock from existing warehouse to new warehouse

-

### **Activation**

Go to Setup > Accounts Settings > check "Make Accounting Entry For Every Stock Entry"

![Activation](img/activate-accounting-for-stock.png)

-

### **What Will It Do For You?**

It will make it easier for you to maintain accuracy of company's stock-in-hand, fixed-assets and cost-of-goods-sold. Stock balances will always be synced with relevant account balances, so no more periodic manual entry to balance them.

In case of new back-dated stock transactions or cancellation/amendment of an existing one, all the future Stock Ledger entries and GL Entries will recalculated for all related items.

The same is applicable if any cost is added to Purchase Receipt through Landed Cost Wizard.

-

### **What Will It Not Do For You?**

It will not affect accounting of existing stock transactions submitted prior to the activation of Perpetual Accounting.
Auto / Perpetual Accounting totally depends upon the item valuation rate. Hence, you have to be more careful entering valuation rate while making Purchase Receipt, Material Receipt or Manufacturing / Repack

-

### **Example**

>Consider following Chart of Accounts and Warehouse setup for your company:

>#### Chart of Accounts

>- Assets (Dr)
>  - Current Assets
>    - Accounts Receivable
>      - Jane Doe
>    - Stock Assets
>      - Stock In Hand
>    - Tax Assets
>      - VAT
>  - Fixed Assets
>    - Office Equipments
>- Liabilities (Cr)
>  - Current Liabilities
>    - Accounts Payable
>      - East Wind Inc.
>    - Stock Liabilities
>      - Stock Received But Not Billed
>    - Tax Liabilities
>      - Service Tax
>- Income (Cr)
>  - Direct Income
>    - Sales Account
>- Expenses (Dr)
>  - Direct Expenses
>    - Stock Expenses
>      - Cost of Goods Sold
>      - Expenses Included In Valuation
>      - Stock Adjustment
>      - Shipping Charges
>      - Customs Duty
  
>#### Warehouse - Account Configuration

>- Stores - Raw Materials
>- Work In Progress - Raw Materials
>- Finished Goods - Finished Goods
>- Fixed Asset Warehouse - Office Equipments

#### **Purchase Receipt**

Suppose you have purchased *10 quantity* of item "RAM" at *$200* and *5 quantity* of item "Table" at **$100** from supplier "East Wind Inc". Following are the details of Purchase Receipt:


>**Supplier:** East Wind Inc.

>**Items:**

>- Item = RAM ; Warehouse = Stores ; Qty = 10 ; Rate = 200 ; Amount = 2000 ; Valuation Amount = 2200
>- Item = Chair ; Warehouse = Fixed Asset Warehouse ; Qty = 5 ; Rate = 100 ; Amount = 500 ; Valuation Amount = 550

>**Taxes:**
>
>- Shipping Charges = 100 ; Total and Valuation
>- VAT = 120 ; Total
>- Customs Duty = 150 ; Valuation


**GL Entry**

<table class="table table-bordered">
  <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
  <tbody>
  <tr><td>Raw Materials</td><td>2000 + 80 + 120 = 2200</td><td>0</td></tr>
  <tr><td>Office Equipments</td><td>500 + 20 + 30 = 550</td><td>0</td></tr>
  <tr><td>Stock Received But Not Billed</td><td>0</td><td>2750</td></tr>
  </tbody>
</table>

--

#### **Purchase Invoice**


>**Supplier:** East Wind Inc.

>**Items:**

>- Item = RAM ; Warehouse = Stores ; Qty = 10 ; Rate = 200 ; Amount = 2000
>- Item = Chair ; Warehouse = Fixed Asset Warehouse ; Qty = 5 ; Rate = 100 ; Amount = 500

>**Taxes:**

>- Shipping Charges = 100 ; Total and Valuation
>- VAT = 120 ; Total
>- Customs Duty = 150 ; Valuation


**GL Entry**

<table class="table table-bordered">
  <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
  <tbody>
  <tr><td>East Wind Inc.</td><td>0</td><td>2500 + 100 + 120 = 2720</td></tr>
  <tr><td>Stock Received But Not Billed</td><td>2500 + 100 + 150 = 2750</td><td>0</td></tr>
  <tr><td>Shipping Charges</td><td>100</td><td>0</td></tr>
  <tr><td>VAT</td><td>120</td><td>0</td></tr>
  <tr><td>Expenses Included In Valuation</td><td>0</td><td>100 + 150 = 250</td></tr>
  </tbody>
</table>

--

### Delivery Note


>**Customer:** Jane Doe

>**Items:**

>- Item = RAM ; Warehouse = Stores ; Qty = 5 ; Rate = 200 ; Amount = 1000 ; Buying Amount = (2200/10)*5 = 1100

>**Taxes:**

>- VAT = 80
>- Service Tax = 50

**GL Entry**

<table class="table table-bordered">
  <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
  <tbody>
  <tr><td>Raw Materials</td><td>0</td><td>1100</td></tr>
  <tr><td>Cost of Goods Sold</td><td>1100</td><td>0</td></tr>
  </tbody>
</table>

--

### Sales Invoice

>**Customer:** Jane Doe

>**Items:**

>- Item = RAM ; Qty = 5 ; Rate = 100 ; Amount = 500

>**Taxes:**

>- VAT = 80
>- Service Tax = 50

**GL Entry**

Item Valuation Rate for this transaction = 750 / 10 = 75

<table class="table table-bordered">
  <thead><tr><th>Account</th><th>Debit</th><th>Credit</th></tr></thead>
  <tbody>
  <tr><td>Jane Doe</td><td>500 + 80 + 50 = 630</td><td>0</td></tr>
  <tr><td>VAT</td><td>0</td><td>80</td></tr>
  <tr><td>Service Tax</td><td>0</td><td>50</td></tr>
  <tr><td>Sales Account</td><td>0</td><td>500</td></tr>
  </tbody>
</table>

--
