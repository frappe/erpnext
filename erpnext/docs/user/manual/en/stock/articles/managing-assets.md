<h1>Managing Assets</h1>

<h1>Managing Assets</h1>

Items like machinery, furniture, land and property, patents etc. can be categorized as fixed asset of a company. In ERPNext, you can maintain fixed asset items in a separate Warehouse.

Item can be created for each type of an asset. Whereas unique Serial No. will be created for each unit of that asset item. Maintaining serialized inventory of asset item will have in tracking item's warranty and expiry details.

####Fixed Asset Master

While creating Item Code for the fixed asset item, you should updated field "Is Fixed Asset" as "Yes".

![Fixed Asset Item]({{docs_base_url}}/assets/img/articles/$SGrab_383.png)

Other item properties like Stock/Non-stock item can be updated on the nature of asset. Like patent and trademarks will be non-stock assets.

If your asset item is serialized, click [here](https://erpnext.com/user-guide/stock/serialized-inventory) to learn how serialized inventory is managed in ERPNext.

####Warehouse for Fixed Asset

Separate Warehouse should be created for the fixed asset items. All the sales, purchase and stock transactions for asset items will be done in that fixed asset warehouse only.

Also, as per the perpetual inventory valuation system, you will have accounting ledger auto-created for the warehouse. You can move the accounting ledger of warehouse created for fixed asset from Stock Asset group to fixed asset group. This will be helpful while preparing financial statement for a company.
<!-- markdown -->