<h1>Set Precision for Float, Currency and Percent fields</h1>

In ERPNext, default precision for `Float`, `Currency` and `Percent` field is 3. So, you can enter any number up-to 3 decimals in such fields.

You can also change / customize the precision settings globally or for a specific field.

To change the precision globally, go to `Setup > Settings > System Settings`.
![Global Precision]({{docs_base_url}}/assets/img/articles/precision-global.png)

You can also set field specific precision. To do that go to `Setup > Customize > Customize Form` and select the DocType there. Then go to the specific field row and change precision. Precision field is only visible if field-type is one of the Float, Currency and Percent.
![Field-wise Precision]({{docs_base_url}}/assets/img/articles/precision-fieldwise.png)

**Note:**
If you are changing precision of a field to a higher number, all the related fields should also be set to the same precision.

For example, if you want to calculate invoice total upto 5 decimals, you need to change the precision of all related fields, which resulted total. In this case you have to change following fields to get correct total.

    Sales Invoice Item: price_list_rate, base_price_list_rate, rate, base_rate, amount and base_amount
    
    Taxes and Charges: tax_amount, total and tax_amount_after_discount
    
    Sales Invoice: net_total, other_charges_total, discount_amount and grand_total

And precision should be changed in all related documents as well, to get correct mapping. In this case, same precision should be set for Quotation, Sales order, Delivery Note and Sales Invoice.

<!-- markdown -->