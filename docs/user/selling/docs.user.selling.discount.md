---
{
	"_label": "Discount"
}
---


While making your sales transactions like a Quotation (or Sales Order) you would already have noticed that there is a “Discount” column. On the left is the “Price List Rate” on the right is the “Basic Rate”.  You can add a “Discount” value to update the basic rate.

Since your taxes are calculated on Items, you must apply your discounts here so that you apply the tax on the discounted rate, which is the case for most taxes.

The second way to apply discount is to add it in your Taxes and Charges table. This way you can explicitly show the Customer the discount you have applied on the order. If you choose this method, remember that you will tax your Customer at the full rate, not the discounted rate. So this is not a good way to track discounts.

There is a third way to do it. Create an Item called “Discount” and make sure that all the taxes apply in the same way as the main Items. (This method is useful if only one type of tax is applicable on the sale). This way your “Discount” will appear as an expense. You will see a slightly higher income and expense but your profits will still remain the same. This method might be interesting where you want detailed accounting of your discounts.

> Note: The maximum Discount that can be applied on an Item can be fixed in the Item master.