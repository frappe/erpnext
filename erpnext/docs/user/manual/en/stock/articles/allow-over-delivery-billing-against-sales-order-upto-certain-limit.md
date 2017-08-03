# Allow Over Delivery Billing Against Sales Order Upto Certain Limit

#Allow Over Delivery/Billing

While creating Delivery Note, system validates if item's Qty mentined is same as in the Sales Order. If Item Qty has been increased, you will get over-delivery validation. If you want to be able to deliver more items than mentioned in the Sales Order, you should update "Allow over delivery or receipt upto this percent" in the Item master.

<img alt="Item wise Allowance percentage" class="screenshot" src="/docs/assets/img/articles/allowance-percentage-1.png">

Item's and Rate is also validated when creating Sales Invoice from Sales Order. Also when creating Purchase Receipt and Purchaes Invoice from Purchase Order. Updating "Allow over delivery or receipt upto this percent" will be affective in all sales and purchase transactions.

For example, if you have ordered 100 units of an item, and if item's over receipt percent is 50%, then you are allowed to make Purchase Receipt for upto 150 units.

Update global value for "Allow over delivery or receipt upto this percent" from Stock Settings. Value updated here will be applicable for all the items.

1. Go to `Stock > Setup > Stock Settings`

2. Set `Allowance Percentage`.

3. Save Stock Settings.

<img alt="Item wise Allowance percentage" class="screenshot" src="/docs/assets/img/articles/allowance-percentage-2.png">


<!-- markdown -->
