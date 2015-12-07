# Re-Order 

# How To Setup Re-order Level?

Go to the Re-order section of the Item form in the Stock module.

> Stock > Item

The Re-order level is the point at which stock on a particular item has diminished to a point where it needs to be replenished. To order based on Re-order level can avoid shortages. Re-order level can be determined based on the lead time and the average daily consumption.

![Reorder Level]({{docs_base_url}}/assets/old_images/erpnext/faq-reorder-level.png)

__For example:__ You can set your reorder level of bath towels at 10. When there are only 10 towels remaining in stock, the system will either send a mail or take action depending upon what you have selected in global settings.

# How To Setup Reorder Quantity?

To setup Reorder quantity, go to the Re-order section of the Item form. In the field ‘Re-order Qty’ type the amount that is needed.

> Stock> Item

Re-order quantity is the quantity to order, so that the sum of ordering cost and holding cost is at its minimum.The re-order quantity is based on the minimum order quantity specified by the supplier and many other factors.

![Reorder Quantity]({{docs_base_url}}/assets/old_images/erpnext/faq-reorder-qty.png)

__For example:__ If reorder level is 100 items, your reorder quantity may not necessarily be 100 items. The Reorder quantity can be greater than or equal to reorder level. It may depend upon lead time, discount, transportation and average daily consumption.

