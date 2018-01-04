# Re-order Level & Re-order Qty

The **Re-order Level** is the point at which stock on a particular item has diminished to a point where it needs to be replenished. To order based on Re-order level can avoid shortages. Re-order level can be determined based on the lead time and the average daily consumption.

You can update Re-order Level and Re-order Qty for an Item in the Auto Re-order section.

For example, you can set your reorder level of Motherboard at 10. When there are only 10 Motherboards remaining in stock, the system will either automatically create a Material Request in your ERPNext account.

**Re-order quantity** is the quantity to order, so that the sum of ordering cost and holding cost is at its minimum.The re-order quantity is based on the minimum order quantity specified by the supplier and many other factors.

For example, If reorder level is 100 items, your reorder quantity may not necessarily be 100 items. The Reorder quantity can be greater than or equal to reorder level. It may depend upon lead time, discount, transportation and average daily consumption.

<img alt="Item Reorder" class="screenshot" src="/docs/assets/img/stock/item-reorder.png">