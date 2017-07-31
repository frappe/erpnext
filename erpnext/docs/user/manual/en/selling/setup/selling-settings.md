# Selling Settings

Selling Setting is where you can define propertiese which will be applied in your selling transactions. 
Let's check into each property one by one.

<img class="screenshot" alt="Selling Settings" src="/docs/assets/img/selling/selling-settings.png">

####1. Customer Naming By

When customer is saved, system generated unique ID for that Customer. Using that Customer ID, 
you can select Customer in other transactions.

Bydefault Customer will be saved with Customer Name. If you wish to save Customer using 
a naming series, you should set Customer Naming By as "Naming Series".

Example of Customer Id's saved in Naming Series - `CUST00001,CUST00002, CUST00003...` and so on.

You can set Naming Series for customer naming from:

> Setup > Settings > Naming Series`

####2. Campaign Naming By

Just like for Customer, you can also configure as how ID will be generated for the Campaign master. 
Bydefault Campaign will be saved with Campaign Name provided while its creation.

####3. Default Customer Group

Customer Group in this field will be auto-updated when you open new Customer form.
While converting Quotation created for Lead into Sales Order, system attempts to convert 
Lead into Customer in the backend. While creating Customer in the backend, system pickup 
Customer Group and Territory as defined in the Selling Setting. If system doesn't find 
any values, then following validation message will be raised.
To resolve this, you should:
Either manually convert Lead into Customer, and define Customer Group and Territory manually while 
creating Customer or define Default Customer Group and Territory in the Selling Setting. 
Then you should have Lead automatically converted into Customer when convert Quotation into Sales Order.

####4. Default Territory

Territory defined in this field will be auto-updated in the Territory field of Customer master.

Just like Customer Group, Territory is also checked when system tries creating Customer in the backend.

####5. Default Price List

Price List set in this field will be auto-updated in the Price List field of Sales transactions.

####6. Sales Order Required

If you wish to make Sales Order creation mandatory before creation of Sales Invoice, then you should 
set Sales Order Required field as Yes. Bydefault, this will be "No" for a value.

####7. Delivery Note Required

To make Delivery Note creation as mandatory before Sales Invoice creation, you should set 
this field as "Yes". It will be "No" by default.

####8. Maintain Same Rate Throughout Sales Cycle

System bydefault validates that item price will be same throughout sales cycle 
(Sales Order - Delivery Note - Sales Invoice). If you could have item price changing within the cycle, 
and you need to bypass validation of same rate throughout cycle, then you should uncheck this field and save.

####9. Allow User to Edit Price List Rate in Transaction

Item table of the sale transactions has field called Price List Rate. This field be non-editale 
by default in all the sales transactions. This is to ensure that price of an item is fetched from 
Item Price record, and user is not able to edit it.

If you need to enable user to edit Item Price, fetched from Price List of an item, you should uncheck this field.

{next}
