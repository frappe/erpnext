---
{
	"_label": "Accounting of Inventory / Stock"
}
---

The value of available inventory is treated as an Asset in company's Chart of Accounts. Depending on the type of items, it can be treated as Fixed Asset or Current Asset. To prepare Balance Sheet, you should make the accounting entries for those assets. 
There are generally two different methods of accounting for inventory:


### **Auto / Perpetual Inventory**

In this process, for each stock transactions system posts relevant accounting entries to sync stock balance and accounting balance. This is the default settings in ERPNext for new accounts.

When you buy and receive items, those items are booked as the company’s assets (stock-in-hand / fixed-assets). When you sell and deliver those items, an expense (cost-of-goods-sold) equal to the buying cost of the items is booked. General Ledger entries are made after every stock transaction. This improves accuracy of Balance Sheet and Profit and Loss statement. And the value as per Stock Ledger always remains same with the relevant account balance.

To check accounting entries for a particular stock transaction, please check [**examples**](docs.user.stock.perpetual_inventory.html)

#### **Advantages**

It will make it easier for you to maintain accuracy of company's stock-in-hand, fixed-assets and cost-of-goods-sold. Stock balances will always be synced with relevant account balances, so no more periodic manual entry to balance them.

In case of new back-dated stock transactions or cancellation/amendment of an existing one, all the future Stock Ledger entries and GL Entries will recalculated for all related items.
The same is applicable if any cost is added to submitted Purchase Receipt later through Landed Cost Wizard.

>Note: Perpetual Inventory totally depends upon the item valuation rate. Hence, you have to be more careful entering valuation rate while making any incoming stock transaction like Purchase Receipt, Material Receipt or Manufacturing / Repack

-

### **Periodic Inventory**

In this method, accounting entries are manually created periodically to sync stock balance and relevant account balance. The system does not create accounting entries automatically for assets, at the time of material purchases or sales.

In an accounting period, when you buy and receive items, an expense is booked in your accounting books. You sell and deliver some of these items.

At the end of an accounting period, the total value of items, that remain to be sold, need to be booked as the company’s assets, often known as stock-in-hand. 

The difference between the value of the items remaining to be sold and the previous period’s stock-in-hand can be positive or negative. If positive, this value is removed from expenses (cost-of-goods-sold) and is added to assets (stock-in-hand / fixed-assets). If negative, a reverse entry is passed. 

This complete process is called Periodic Inventory.

If you are an existing user using Periodic Inventory and want to use Perpetual Inventory, check [**Migration From Periodic Inventory**](docs.user.stock.perpetual_inventory.html)
