One of the primary motivator for compulsory use of accounting tools is
calculation of Taxes. You may or may not make money but your government will
(to help your country be safe and prosperous). And if you don’t calculate your
taxes correctly, they get very unhappy. Ok, philosophy aside, ERPNext allows
you to make configurable tax templates that you can apply to your sales or
purchase.

### Tax Accounts

For Tax Accounts that you want to use in the tax templates, you must go to
Chart of Accounts and mention them as type “Tax” in your Chart of Item.

## Item Tax

If some of your Items require different tax rates as compared to others,
mention them in the Item tax table. Even if you have selected your sales and
purchase taxes as default tax rates, the system will pull the Item tax rate
for calculations. Item tax will get preference over other sales or purchase
taxes. However, if you wish to apply default sales and purchase taxes, do not
mention item tax rates in the Item master. The system will then select the
sales or purchase tax rate specified by you as default rates.

Item Tax table can be found as a section within the Item Master document.

<img class="screenshot" alt="Item Tax" src="{{docs_base_url}}/assets/img/taxes/item-tax.png">

  * **Inclusive and Exclusive Tax**: ERPNext allows you to enter Item rates which are tax inclusive.

<img class="screenshot" alt="Inclusive Tax" src="{{docs_base_url}}/assets/img/taxes/inclusive-tax.png">

  * **Exception to the rule**: Item tax settings are required only if a particular Item has a different tax rate than the rate defined in the standard tax Account
  * **Item tax is overwrite-able**: You can overwrite or change the item tax rate by going to the Item master in the Item tax table.

## Sales Taxes and Charges Template

You must usually collect taxes from your Customer and pay them to the
government. At times, you may have to pay multiple taxes to multiple
government bodies like local government, state or provincial and federal or
central government.

The way ERPNext sets up taxes is via templates. Other types of charges that
may apply to your invoices (like shipping, insurance etc.) can also be
configured as taxes.

Select template and modify as per your need.

To create a new sales tax template called Sales Taxes and Charges Template, you
have to go to:

> Setup > Accounts > Sales Taxes and Charge Master

<img class="screenshot" alt="Sales Tax Master" src="{{docs_base_url}}/assets/img/taxes/sales-tax-master.png">

When you create a new master, you will have to add a row for each tax type.

The tax rate you define here will be the standard tax rate for all Items. If
there are Items that have different rates, they must be added in the Item Tax
table in the Item master.

In each row, you have to mention:

  * Calculation Type:

    * On Net Total : This can be on net total (total amount without taxes).
    * On Previous Row Total/Amount: You can apply taxes on previous row total / amount. If you select this option, the tax will be applied as a percentage of the previous row (in the tax table) amount or total. Previous row amount means a particular tax amount.And, previous row total means net total plus taxes applied up to that row. In the Enter Row Field, mention row number on which you want to apply the current tax. If you want to apply the tax on the 3rd row, mention "3" in the Enter Row field.

    * Actual : Enter as per actual amount in rate column.

  * Account Head: The Account ledger under which this tax will be booked

  * Cost Center: If the tax / charge is an income (like shipping) it needs to be booked against - a Cost Center.
  * Description: Description of the tax (that will be printed in invoices / quotes).
  * Rate: Tax rate.
  * Amount: Tax amount.
  * Total: Cumulative total to this point.
  * Enter Row: If based on "Previous Row Total" you can select the row number which will be taken as a base for this calculation (default is the previous row).
  * Is this Tax included in Basic Rate?: If you check this, it means that this tax will not be shown below the item table, but will be included in the rate in your main item table. This is useful when you want to give a flat price (inclusive of all taxes) to your customers.

Once you setup your template, you can select this in your sales transactions.

## Purchase Taxes and Charges Template

Similar to your Sales Taxes and Charges Template is the Purchase Taxes and
Charges Master.

This is the tax template that you can use in your Purchase Orders and Purchase
Invoices. If you have value added taxes (VAT), where you pay to the government
the difference between your incoming and outgoing taxes, you can select the
same Account that you use for sales taxes.

The columns in this table are similar to the Sales Taxes and Charges Template
with the difference as follows:

Consider Tax or Charge for: In this section you can specify if the tax /
charge is only for valuation (not a part of total) or only for total (does not
add value to the item) or for both.

{next}

