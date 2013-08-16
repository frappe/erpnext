---
{
	"_label": "Setting up Taxes"
}
---
One of the primary motivator for compulsory use of accounting tools is calculation of Taxes. You may or may not make money but your government will (to help your country be safe and prosperous). And if you don’t do your taxes correctly, they get very unhappy. Ok, philosophy aside, ERPNext allows you to make configurable tax templates that you can apply to your sales or purchase.

### Tax Accounts

For Tax Accounts that you want to use in the tax templates, you must mention them as type “Tax” in your Chart of Accounts.

## Sales Taxes and Charges Master

You must usually collect taxes from your Customer and pay them to the government. At times, you may have to pay multiple taxes to multiple government bodies like local government, state or provincial and federal or central government.

The way ERPNext sets up taxes is via templates. Other types of charges that may apply to your invoices (like shipping, insurance etc.) can also be configured as taxes.

To create a new sales tax template called Sales Taxes and Charges Master, you have to go to:

> Selling > Setup (sidebar) > Sales Taxes and Charge Master

When you create a new master, you will have to add a row for each tax type.

The tax rate you define here will be the standard tax rate for all Items. If there are Items that have different rates, they must be added in the Item Tax table in the Item master.

In each row, you have to mention:

- Calculation Type: 
	- This can be on net total (that is your basic amount).
	- On previous row total / amount (for cumulative taxes or charges). If you select this 	option, the tax will be applied as a percentage of the previous row (in the tax table) amount or total.
	- Actual (as mentioned).
- Account Head: The Account ledger under which this tax will be booked
- Cost Center: If the tax / charge is an income (like shipping) it needs to be booked against - a Cost Center.
- Description: Description of the tax (that will be printed in invoices / quotes).
- Rate: Tax rate.
- Amount: Tax amount.
- Total: Cumulative total to this point.
- Enter Row: If based on "Previous Row Total" you can select the row number which will be taken as a base for this calculation (default is the previous row).
- Is this Tax included in Basic Rate?: If you check this, it means that this tax will not be shown below the item table, but will be included in the rate in your main item table. This is useful when you want to give a flat price (inclusive of all taxes) to your customers.

Once you setup your template, you can select this in your sales transactions.

## Purchase Taxes and Charges Master

Similar to your Sales Taxes and Charges Master is the Purchase Taxes and Charges Master.

This is the tax template that you can use in your Purchase Orders and Purchase Invoices. If you have value added taxes (VAT), where you pay to the government the difference between your incoming and outgoing taxes, you can select the same Account that you use for sales taxes.

The columns in this table are similar to the Sales Taxes and Charges Master with the difference as follows:

Consider Tax or Charge for: In this section you can specify if the tax / charge is only for valuation (not a part of total) or only for total (does not add value to the item) or for both.
