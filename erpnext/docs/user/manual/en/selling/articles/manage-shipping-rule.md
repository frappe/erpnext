<h1>Manage Shipping Rule</h1>

Shipping Rule master help you define rules based on which shipping charge will be applied on sales transactions.

Most of the companies (mainly retail) have shipping charge applied based on invoice total. If invoice value is above certain range, then shipping charge applied will be lesser. If invoice total is less, then shipping charges applied will be higher. You can setup Shipping Rule to address the requirement of varying shipping charge based on total.

To setup Shipping Rule, go to:

Selling/Accounts >> Setup >> Shipping Rule

Here is an example of Shipping Rule master:

![Shipping Rule Master]({{docs_base_url}}/assets/img/articles/$SGrab_258.png)

Referring above, you will notice that shipping charges are reducing as range of total is increasing. This shipping charge will only be applied if transaction total falls under one of the above range, else not.

If shipping charges are applied based on Shipping Rule, then more values like Shipping Account, Cost Center will be needed as well to add row in the Taxes and Other Charges table of sales transaction. Hence these details are tracked as well in the Shipping Rule itself.

![Shipping Rule Filters]({{docs_base_url}}/assets/img/articles/$SGrab_260.png)

Apart from price range, Shipping Rule will also validate if its territory and company matches with that of Customer's territory and company.

Following is an example of how shipping charges are auto-applied on sales order based on Shipping Rule.

![Shipping Rule Application]({{docs_base_url}}/assets/img/articles/$SGrab_261.png)