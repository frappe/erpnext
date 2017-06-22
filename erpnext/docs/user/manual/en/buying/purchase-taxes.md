For Tax Accounts that you want to use in the tax templates, you must mention
them as type “Tax” in your Chart of Accounts.

Similar to your Sales Taxes and Charges Template is the Purchase Taxes and
Charges Master. This is the tax template that you can use in your Purchase
Orders and Purchase Invoices.

> Buying > Setup > Purchase Taxes and Charges Template > New Purchase Taxes and Charges
Master

![Purchase-Taxes]({{docs_base_url}}/assets/img/buying/purchase-taxes.png)


You can specify if the tax / charge is only for valuation (not a part of
total) or only for total (does not add value to the item) or for both.

If you select a particular tax as your Default tax, the system will apply this
tax to all the purchase transactions by default. 

### Calculation Type

This can be on Net Total (that is the sum of basic amount). On Previous Row
Total / Amount (for cumulative taxes or charges). If you select this option,
the tax will be applied as a percentage of the previous row (in the tax table)
amount or total. Actual (as mentioned).

  * **Account Head:** The Account ledger under which this tax will be booked.
  * **Cost Center:** If the tax / charge is an income (like shipping) or expense it needs to be booked against a Cost Center.
  * **Description:** Description of the tax (that will be printed in invoices / quotes).
  * **Rate:** Tax rate.
  * **Amount:** Tax amount.
  * **Total:** Cumulative total to this point.
  * **Enter Row:** If based on "Previous Row Total" you can select the row number which will be taken as a base for this calculation (default is the previous row).
  * **Consider Tax or Charge for:** In this section you can specify if the tax / charge is only for valuation (not a part of total) or only for total (does not add value to the item) or for both.
  * **Add or Deduct:** Whether you want to add or deduct the tax.

{next}
