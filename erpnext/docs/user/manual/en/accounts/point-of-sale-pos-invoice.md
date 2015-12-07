# Point of Sale Invoice

Point of Sale (POS) is the place where a retail transaction is completed. It
is the point at which a customer makes a payment to the merchant in exchange
for goods or services. For retail operations, the delivery of goods, accrual
of sale and payment all happens in one event, that is usually called the
“Point of Sale”.

You can make a Sales Invoice of type POS by checking on “Is POS”. When you
check this, you will notice that some fields get hidden and some new ones
emerge.

> Tip: In retail, you may not create a separate Customer record for each
customer. You can create a general Customer called “Walk-in Customer” and make
all your transactions against this Customer record.

#### Setting Up POS

In ERPNext all Sales and Purchase transactions, like Sales Invoice, Quotation, Sales Order, Purchase Order etc. can be edited via the POS. There two steps to Setup POS:

1. Enable POS View via (Setup > Customize > Feature Setup)
2. Create a [POS Setting]({{docs_base_url}}/user/manual/en/setting-up/pos-setting.html) record

#### Switch to POS View

Open any sales / purchase transaction. Click on the Computer <i class="icon-desktop"></i> Icon.

#### Different sections of the POS

  * Update Stock: If this is checked, Stock Ledger Entries will be made when you “Submit” this Sales Invoice thereby eliminating the need for a separate Delivery Note.
  * In your Items table, update inventory information like Warehouse (saved as default), Serial Number, or Batch Number if applicable.
  * Update Payment Details like your Bank / Cash Account, Paid amount etc.
  * If you are writing off certain amount. For example when you receive extra cash as a result of not having exact denomination of change, check on ‘Write off Outstanding Amount’ and set the Account.

### Adding an Item

At the billing counter, the retailer needs to select Items which the consumer
buys. In the POS interface you can select an Item by two methods. One, is by
clicking on the Item image and the other, is through the Barcode / Serial No.

**Select Item** \- To select a product click on the Item image and add it into the cart. A cart is an area that prepares a customer for checkout by allowing to edit product information, adjust taxes and add discounts.

**Barcode / Serial No** \- A Barcode / Serial No is an optical machine-readable representation of data relating to the object to which it is attached. Enter Barcode / Serial No in the box as shown in the image below and pause for a second, the item will be automatically added to the cart.

![POS]({{docs_base_url}}/assets/old_images/erpnext/pos-add-item.png)

> Tip: To change the quantity of an Item, enter your desired quantity in the
quantity box. These are mostly used if the same Item is purchased in bulk.

If your product list is very long use the Search field, type the product name
in Search box.

### Removing an Item

There are two ways to remove an Item.

  * Select an Item by clicking on the row of that Item from Item cart. Then click on “Del” button. OR

  * Enter 0(zero) quantity of any item to delete that item.

To remove multiple Items together, select multiple rows & click on “Del”
button.

> Delete button appears only when Items are selected.

![POS]({{docs_base_url}}/assets/old_images/erpnext/pos-remove-item.png)

### Make Payment

After all the Items and their quantities are added into the cart, you are
ready to make the Payment. Payment process is divided into 3 steps -

  1. Click on “Make Payment” to get the Payment window.
  2. Select your “Mode of Payment”.
  3. Click on “Pay” button to Save the document.

![POS Payment]({{docs_base_url}}/assets/old_images/erpnext/pos-make-payment.png)

Submit the document to finalise the record. After the document is submitted,
you can either print or email it directly to the customer.

#### Accounting entries (GL Entry) for a Point of Sale:

Debits:

  * Customer (grand total) 
  * Bank / Cash (payment)

Credits:

  * Income (net total, minus taxes for each Item) 
  * Taxes (liabilities to be paid to the government)
  * Customer (payment)
  * Write Off (optional)

To see entries after “Submit”, click on “View Ledger”.

{next}
