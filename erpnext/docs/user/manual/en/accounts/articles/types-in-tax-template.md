# Types in Sales and Purchase Tax Template

In the Sales Taxes and Purchase Taxes master, you will find a column called Type. Following a brief on a meaning of each Type and how you can use it.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/types-in-tax-masters.png">

**Actual:** This allows you to enter expense amount directly. For example, Rs. 500 incurred for Shipping.

**On Net Total:** If you want to apply any tax or charges on Net Total, select this option. For example, 18% GST applied to all the item in the Sales Order.

**On Previous Row Amount:** This option helps you want to calculate tax amount calculated based on another tax amount.

Example: Education Cess is calculated based on the amount of GST tax.

**On Previous Row Total:** For each Tax row, a cumulative tax is calculated in the Total column. For the first row, total tax is calculated as Net Total + Tax amount at first row. If you want to apply a tax on the Total Amount of another tax row, then use this option.

If you select Type as Previous Row Amount or Previous Row Total, then you must also specify a Row No. whose Amount or Total should be considered for the calculation.