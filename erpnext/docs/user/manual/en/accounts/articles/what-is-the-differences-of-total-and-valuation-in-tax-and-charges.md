#Purchase Tax or Charges Categories

Consider Tax or Charge field in Purchase Taxes and Charges master has three values.

- Total
- Valuation
- Total and Valuation

<img alt="Purchase Tax and Charges Categories" class="screenshot" src="{{docs_base_url}}/assets/img/articles/purchase-other-charges-1.png">

Let's consider an example to understand an effect of each charge type. We purchase ten units of item, at the rate of 800. total purchase amount is 800. Purchased item has 4% VAT applied on it, and INR 100 was incurred in transportation.

####Total:

Tax or Charge categorized as **Total** will be included in the total of purchase transactions. But it will not have impact on the valuation of item purchased.

If VAT 4% is applied on item, it will amount to INR 32 (at item's based rate is 800). Since VAT is the [consumption tax](https://frappe.io/blog/erpnext-features/managing-consumption-tax), its should be added value of Purchase Order/Invoice, since it will be included in payable towards supplier. But its should not be added to the value of Purchased item.

When Purchase Invoice is submitted, general ledger posting will be done for tax/charge categorized as Total.

####Valuation:

Tax or charge categorized as **Valuation** will be added in the value of purchased item, but not in the total of that purchase transaction.

Transportation charge of INR 100 should be categorized as valuation. With this, the value of purchased item will be increased from 800 to 900. Also, this charge will be not be added to the total of purchase transaction, because it your expense, and should not be reflected to the supplier.

Check [here]({{docs_base_url}}/user/manual/en/stock/accounting-of-inventory-stock/perpetual-inventory.html) to learn general posting done for expense categorized as Valuation.

####Total and Valuation:

Tax or Charge categorized as for **Total and Valuation** will be added in the valuation of item, as well as in the totals of purchase transactions.

Let's assume that transportion is arranged by our supplier, but we need to pay transportation charges to them. In that case, for transportation charges, category selected should be Total and Valuation. With this, INR 100 transportation charge will be added to the actual purchase amount 800. Also, INR 100 will reflect in the total, as it will be payable for us towards supplier.