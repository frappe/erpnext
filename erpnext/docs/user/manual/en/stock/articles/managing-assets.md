#Managing Assets

Items like machinery, furniture, land and property, patents etc. can be categorized as fixed asset of a company. In ERPNext, you can maintain fixed asset items, mainly stock items in a separate Warehouse.

For the high value asset items, serialized inventory can be maintained. It will allow assigning unique Serial No. to each unit of an asset item.

####Fixed Asset Master

While creating Item Code for the fixed asset item, you should check "Is Fixed Asset" field.

<img alt ="Fixed Asset Item" class="screenshot" src="{{docs_base_url}}/assets/img/articles/managing-assets-1.png">

Other item properties like Stock/Non-stock item can be updated on the nature of asset. Like patent and trademarks will be non-stock assets.

If your asset item is serialized, click [here]({{docs_base_url}}/user/videos/learn/serialized-inventory.html) to learn how serialized inventory is managed in ERPNext.

####Warehouse for Fixed Asset

Separate Warehouse should be created for the fixed asset items. All the sales, purchase and stock transactions for asset items should be done for fixed asset warehouse only.

As per the perpetual inventory valuation system, accounting ledger is auto-created for a warehouse. You can move the accounting ledger of fixed asset from Stock Asset (default group) to Fixed Asset's group account.

<!-- markdown -->
