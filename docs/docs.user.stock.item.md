---
{
	"_label": "Item Master",
	"_title_image": "img/items.png"
}
---
Items, Customers and Suppliers form the foundation of any ERP system.

It is very likely you will have your masters ready in another system or a spread sheet and you would just need to import them. Before importing, it might be a good idea to understand how ERPNext treats them a bit first.

---

## Items

An Item is simply a product or service you sell or buy from your Customers or Suppliers. ERPNext is optimized for itemized management of your sales and purchase though you can skip creating Items. If you are in services, you can create an Item for each service that your offer.

> Items are mandatory if you want to track inventory.

There are two main categories of Items in ERPNext

- Stock Items
- Non Stock Items

As you may have guessed, inventory balances are tracked for stock items and not for
non-stock items. Non-stock items could be services or consumables that are not tracked.

### Naming Items

This is a complex topic [coming up next]. In ERPNext you can use item codes or names. If you do not want to codify, you can keep the item name and item code as the same.

### Item Groups

ERPNext allows you to classify items into groups. This will help you in getting reports about various classes of items and also help in cataloging your items for the website.

### Warehouses

In ERPNext you can create Warehouses to identify where your Items reside. 

There are two main Warehouse Types that are significant in ERPNext.

Stores: These are where your incoming Items are kept before they are consumed or sold. You can have as many “Stores” type Warehouses as you wish. Stores type warehouses are significant because if you set an Item for automatic re-order, ERPNext will check its quantities in all “Stores” type Warehouses when deciding whether to re-order or not.

Asset: Items marked as type “Fixed Asset” are maintained in Asset Type Warehouses. This helps you separate them for the Items that are consumed as a part of your regular operations or “Cost of Goods Sold”.

### Item Taxes

These settings are only required if this particular Item has a different tax rate than what is the rate defined in the standard tax Account.

For example, you have a tax Account, “VAT 10%” and this particular item is exempted from this tax, then you select “VAT 10%” in the first column, and set “0” as the tax rate in the second column.

### Inspection

Inspection Required: If an incoming inspection (at the time of delivery from the Supplier) is mandatory for this Item, mention “Inspection Required” as “Yes”. The system will ensure that a Quality Inspection will be prepared and approved before a Purchase Receipt is submitted.

Inspection Criterial: If a Quality Inspection is prepared for this Item, then this template of criteria can will automatically be updated in the Quality Inspection table of the Quality Inspection.  Examples of Criteria are: Weight, Length, Finish etc.

### Item Pricing and Price Lists

ERPNext lets you maintain multiple selling prices for an Item using Price Lists. A Price List is a name you can give to a set of Item prices.
￼
Why would you want Price Lists? You have different prices for different zones (based on the shipping costs), for different currencies, regions etc.

### Item Valuation

How are Items Valued?

One of the major features of any inventory system is that you can find out the value of any item based on its historic or average price. You can also find the value of all your items for your balance sheet. Why is valuation important?

- The buying price fluctuates.
- The value changes because of some process (value add).
- The value changes because of decay, loss etc.

You may encounter these terms, so lets clarify:

- Rate: Rate at which the transaction takes place.
- Valuation Rate: Rate at which the items value is set for your valuation.

There are two major ways in which ERPNext values your items.

- **FIFO (First In First Out):** In this system, ERPNext assumes that you will consume / sell those Items first that you bought first. For example, if you buy an Item at price X and then after a few days at price Y. So when sell your Item, ERPNext will reduce the quantity of the Item priced at X first and then Y.

￼

- **Moving Average:** In this method, ERPNext assumes that the value of the item at any point is the average price of the units of that Item in stock. For example, if the value of an Item is X in a Warehouse with quantity Y and another quantity Y1 is added to the Warehouse at cost X1, the new value X2 would be:

> New Value X2 = (X * Y + X1 * Y1) / (Y + Y1)

#### Negative Stock

FIFO is the more accurate system of the two but has a disadvantage. You cannot have negative stock in FIFO. This means that you cannot make forward transactions that would make your stock negative. Why is this? Because sequences are so important to FIFO, you cannot track the value of the stock if it does not exist!

In Moving Average, since each item has an “average” value, the value of the negative stock is also based on this “average”.

### Serial Numbers and Batches

In scenarios where you may have to track individual units or batches of Items you sell, ERPNext allows you to manage Serial Numbers and Batches.
￼
Why is this useful?

- To track warranty and returns.
- To trace individual Items incase they are recalled by the Supplier.
- To manage expiry.

In ERPNext, Serial Number and Batch are separate entities and all stock transactions for Items that serialized or batches must be tagged with either the Batch or Serial Number.

> Important: Once you mark an item as serialized or batched or neither, you cannot change it after you have make any stock entry.
