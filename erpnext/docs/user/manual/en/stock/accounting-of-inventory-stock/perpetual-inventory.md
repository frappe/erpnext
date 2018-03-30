# Perpetual Inventory

As per the perpetual inventory system, accounts posting is done for every stock transaction.

On creating new Warehouse, the system will automatically create an Account in the Chart of Account, with the same name as Warehouse Name.

On receipt of items in a particular warehouse, the balance in the Warehouse Account will increase. Similarly when items are delivered from the Warehouse, an expense will be booked, and balance in the Warehouse Account will reduce.

##Activation

  * Activate Perpetual Inventory

	 > Setup > Company > Stock Settings > "Enable Perpetual Inventory"

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-1.png">

  * Setup the following default accounts for each Company. These accounts are created automatically in the new ERPNext accounts.

	* Default Inventory Account
    * Stock Received But Not Billed
    * Stock Adjustment Account
    * Expenses Included In Valuation	
    * Cost Center

  * If user wants to set an individual account for each warehouse, create account head for each account under `Assets > Current Asset > Stock Assets > (Warehouse)` and set it on the respective warehouse under field 'Account'.

  * For stock transactions, general ledger entries made against the account head set on the warehouse, if user had not set the account for the warhouse then system gets the account head from the parent warehouse. If account had not set for parent warehouse then system gets the account(Default Inventory Account) from the company master.

* * *

##Example

Consider following Chart of Accounts and Warehouse setup for your company:

####Chart of Accounts

  * Assets (Dr) 
    * Current Assets
    * Accounts Receivable 
      * Debtor
    * Stock Assets 
      * Stores
      * Finished Goods
      * Work In Progress
    * Tax Assets 
      * VAT
    * Fixed Assets
      * Fixed Asset Warehouse
  * Liabilities (Cr) 
    * Current Liabilities
    * Accounts Payable 
      * Creditors
    * Stock Liabilities 
      * Stock Received But Not Billed
    * Tax Liabilities 
      * Service Tax
  * Income (Cr) 
    * Direct Income
    * Sales Account
  * Expenses (Dr) 
    * Direct Expenses
    * Stock Expenses 
      * Cost of Goods Sold
      * Expenses Included In Valuation
      * Stock Adjustment
      * Shipping Charges
      * Customs Duty

####Warehouse - Account Configuration

  * Stores
  * Work In Progress
  * Finished Goods

###Purchase Receipt

Suppose you have purchased _10 nos_ of item "RM0001" at _$200_ and _5 nos_ of item "Base Plate" at **$100** from supplier "Arcu Vel Quam Fabricators". Following are the details of Purchase Receipt:

**Supplier:** Arcu Vel Quam Fabricators

**Items:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Item</th>
            <th>Warehouse</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
            <th>Valuation Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>Stores</td>
            <td>10</td>
            <td>200</td>
            <td>2000</td>
            <td>2250</td>
        </tr>
    </tbody>
</table>
<p><strong>Taxes:</strong>
</p>
<table class="table table-bordered">
    <thead>
        <tr>
            <th>Account</th>
            <th>Amount</th>
            <th>Category</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Shipping Charges</td>
            <td>100</td>
            <td>Total and Valuation</td>
        </tr>
        <tr>
            <td>VAT (10%)</td>
            <td>200</td>
            <td>Total</td>
        </tr>
        <tr>
            <td>Customs Duty</td>
            <td>150</td>
            <td>Valuation</td>
        </tr>
    </tbody>
</table>

**Stock Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-receipt-sl-1.png">

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-receipt-gl-2.png">

As stock balance increases through Purchase Receipt, "Store" accounts are debited and a temporary account "Stock Receipt But Not Billed" account is credited, to maintain double entry accounting system. At the same time, negative expense is booked in account "Expense included in Valuation" for the amount added for valuation purpose, to avoid double expense booking.

* * *

###Purchase Invoice

On receiving Bill from supplier, for the above Purchase Receipt, you will make Purchase Invoice for the same. The general ledger entries are as follows:

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-pinv-gl-3.png">

Here "Stock Received But Not Billed" account is debited and nullified the
effect of Purchase Receipt.

* * *

###Delivery Note

Lets say, you have an order from "Utah Automation Services" to deliver 5 nos of item "RM0001"
at $300. Following are the details of Delivery Note:

**Customer:** Utah Automation Services

**Items:**
<table class="table table-bordered">
    <thead>
        <tr>
            <th>Item</th>
            <th>Warehouse</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>Stores</td>
            <td>5</td>
            <td>300</td>
            <td>1500</td>
        </tr>
    </tbody>
</table>
<p><strong>Taxes:</strong>
</p>
<table class="table table-bordered">
    <thead>
        <tr>
            <th>Account</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Service Tax</td>
            <td>150</td>
        </tr>
        <tr>
            <td>VAT</td>
            <td>100</td>
        </tr>
    </tbody>
</table>

**Stock Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-dn-sl-4.png">

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-dn-gl-5.png">

As item is delivered from "Stores" warehouse, "Stores" account is credited and
equal amount is debited to the expense account "Cost of Goods Sold". The
debit/credit amount is equal to the total valuation amount (buying cost) of
the selling items. And valuation amount is calculated based on your preferred
valuation method (FIFO / Moving Average) or actual cost of serialized items.

    
     
    In this example, we have considered valuation method as FIFO. 
    Valuation Rate  = Purchase Rate + Charges Included in Valuation 
                    = 200 + (250 * (2000 / 2500) / 10) 
                    = 220
    Total Valuation Amount  = 220 * 5 
                            = 1100
        
    

* * *

###Sales Invoice with Update Stock

Lets say, you did not make Delivery Note against the above order and instead
you have made Sales Invoice directly, with "Update Stock" options. The details
of the Sales Invoice are same as the above Delivery Note.

**Stock Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-inv-sl-6.png">

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-inv-gl-7.png">

Here, apart from normal account entries for invoice, "Stores" and "Cost of
Goods Sold" accounts are also affected based on the valuation amount.

* * *

###Stock Entry (Material Receipt)

**Items:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Item</th>
            <th>Target Warehouse</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>Stores</td>
            <td>50</td>
            <td>220</td>
            <td>11000</td>
        </tr>
    </tbody>
</table>

**Stock Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-receipt-sl.png">

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-receipt-gl.png">

* * *

###Stock Entry (Material Issue)

**Items:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Item</th>
            <th>Source Warehouse</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>Stores</td>
            <td>10</td>
            <td>220</td>
            <td>2200</td>
        </tr>
    </tbody>
</table>

**Stock Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-issue-sl.png">

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-issue-gl.png">

* * *

###Stock Entry (Material Transfer)

**Items:**

<table class="table table-bordered">
    <thead>
        <tr>
            <th>Item</th>
            <th>Source Warehouse</th>
            <th>Target Warehouse</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>RM0001</td>
            <td>Stores</td>
            <td>Work In Progress</td>
            <td>10</td>
            <td>220</td>
            <td>2200</td>
        </tr>
    </tbody>
</table>

**Stock Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-transfer-sl.png">

**General Ledger**

<img class="screenshot" alt="Perpetual Inventory" src="{{docs_base_url}}/assets/img/accounts/perpetual-st-transfer-gl.png">
	
{next}