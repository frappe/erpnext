Item Price is the record in which you can log selling and buying rate of an item.

There are two ways to reach to new Item Price form.

> Selling/Buying/Stock >> Setup >> Item Price >> New Item Price

Or

> Item >> Add/Edit Prices >> Click on "+"  >> New Item Price

Following are the steps to create new Item Price.

Step 1: Select Price List

You can create multiple Price List in ERPNext to track Selling and Buying Price List of an item separtely. Also if item's selling prices id changing based on territory, or due to other criteria, you can create multiple selling Price List for it.

![Item Price list]({{docs_base_url}}/assets/old_images/erpnext/item-price-list.png)

On selection of Price List, its currency and for selling or buying property will be fetched as well.

To have Item Price fetching in the sales or purchase transaction, you should have Price List id selected in the transaction, just above Item table.

Step 2: Select Item

Select item for which Item Price record is to be created. On selection of Item Code, Item Name and Description will be fetched as well.

![Item Price Item]({{docs_base_url}}/assets/old_images/erpnext/item-price-item.png)

Step 3: Enter Rate

Enter selling/buying rate of an item in Price List currency.

![Item Price Rate]({{docs_base_url}}/assets/old_images/erpnext/item-price-rate.png)

Step 4: Save Item Price

To check all Item Price together, go to:

Stock >> Main Report >> Itemwise Price List Rate

You will find option to create new Item Price record (+) in this report as well.


Other fields that you can add are:
1. If Selling select the related Customer. This can lead to each Customer have a special selling price.
2. Unit of Measument (UOM) you can specify UOM differently in Item Price from Item for example you keep a stock in Boxes but you need a Item Price per single box unit.
3. Mininum Qty of Item Price, for example 0.002 rate stand only if order are 1000 pieces etc.
4. Lead Time in Days
5. Packing unit, quantity that must be bought or sold per UOM
6. Valid From and Valid Upto. For example an Item Price is Valid that period due a offer period (Christmas)
7. Note is a free text.

{next}
