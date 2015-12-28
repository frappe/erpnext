#Set Precision

In ERPNext, default precision for `Float`, `Currency` and `Percent` field is three. It allows you to enter value having value upto three decimal places.

You can also change/customize the precision settings globally or for a specific field.

To change the precision globally, go to:

`Setup > Settings > System Settings`.

<img alt="Global Precision" class="screenshot" src="{{docs_base_url}}/assets/img/articles/precision-1.png">

You can also set field specific precision. To do that go to `Setup > Customize > Customize Form` and select the DocType there. Then go to the specific field row and change precision. Precision field is only visible if field-type is one of the Float, Currency and Percent.

<img alt="Field-wise Precision" class="screenshot" src="{{docs_base_url}}/assets/img/articles/precision-2.png">

**Note:**

If you are changing precision of a field to a higher number, all the related field's precision should be updated as well. For example, if you want invoice total to be upto five decimals, you should set the precision of all related fields to five decimal places as well.

    | Doctype | Fields |
	|---------|-------:|
	| Sales Invoice Item | price_list_rate, base_price_list_rate, rate, base_rate, amount and base_amount |
    | Taxes and Charges | tax_amount, total and tax_amount_after_discount |
    | Sales Invoice | net_total, other_charges_total, discount_amount and grand_total |

<!-- markdown -->