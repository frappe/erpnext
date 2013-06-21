---
{
	"_label": "Quotation"
}
---
During a sale, the customer may want you to give a written note about the products or services you are planning to offer along with the prices and other terms of engagement. This is called a “Proposal” or an “Estimate” or a “Pro Forma Invoice”or a Quotation.

To create a new Quotation go to:

> Selling > Quotation > New Quotation

A Quotation contains details about:

- Who is the recipient of the Quotation.
- The Items and quantities you are offering.
- The rates at which they are offered.
- The taxes applicable.
- Other charges (like shipping, insurance) if they are applicable.
- The validity of contract.
- The time of delivery.
- Other conditions.

> Tip: Images look great on Quotations. To add images to your Quotations, attach the corresponding image in the Item master.


### Rates

The rates you quote may depend on two things.

- The Price List: If you have multiple Price Lists, you can select a Price List or tag it to the Customer (so that it is auto-selected). Your Item prices will automatically be updated from the Price List.
- The Currency: If you are quoting to a Customer in a different currency, you will have to update the conversion rates so that ERPNext will also save the information in your standard Currency. This will help you to analyze the value of your Quotations in reports in your standard Currency.

### Taxes

To add taxes to your Quotation, you can either select a tax template, Sales Taxes and Charges Master or add the taxes on your own.

You can add taxes in the same manner as the Sales Taxes and Charges Master.

### Terms and Conditions

Each Quotation must ideally contain a set of terms of your contract. It is usually a good idea to make templates of your Terms and Conditions, so that you have a standard set of terms. You can do this by going to:

> Selling > Terms and Conditions  (right sidebar)

#### What should Terms and Conditions Contain?

- Validity of the offer.
- Payment Terms (In Advance, On Credit, part advance etc).
- What is extra (or payable by the Customer).
- Safety / usage warning.
- Warranty if any.
- Returns Policy.
- Terms of shipping, if applicable.
- Ways of addressing disputes, indemnity, liability, etc.
- Address and Contact of your Company.

### Submission

Quotation is a “Submittable” transaction. Since you send this Quotation to your Customer or Lead, you must freeze it so that changes are not made after you send the Quotation.  See Document Stages.

> Tip: Quotations can also be titled as “Proforma Invoice” or “Proposal”. Select the right heading in the “Print Heading” field in the “More Info” section. To create new Print Headings go to Setup > Branding and Printing > Print Headings.

## Dicounts

While making your sales transactions like a Quotation (or Sales Order) you would already have noticed that there is a “Discount” column. On the left is the “Price List Rate” on the right is the “Basic Rate”.  You can add a “Discount” value to update the basic rate.

Since your taxes are calculated on Items, you must apply your discounts here so that you apply the tax on the discounted rate, which is the case for most taxes.

The second way to apply discount is to add it in your Taxes and Charges table. This way you can explicitly show the Customer the discount you have applied on the order. If you choose this method, remember that you will tax your Customer at the full rate, not the discounted rate. So this is not a good way to track discounts.

There is a third way to do it. Create an Item called “Discount” and make sure that all the taxes apply in the same way as the main Items. (This method is useful if only one type of tax is applicable on the sale). This way your “Discount” will appear as an expense. You will see a slightly higher income and expense but your profits will still remain the same. This method might be interesting where you want detailed accounting of your discounts.

> Note: The maximum Discount that can be applied on an Item can up fixed in the Item master.

