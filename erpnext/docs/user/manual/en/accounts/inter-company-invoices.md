
# Inter Company Invoices

Along with creating Purchase Invoices or Sales Invoices for a single company, you can create inter-linked invoices for multiple companies.

Such as, you can create a Purchase Invoice for a company say 'Company ABC', and create a Sales Invoice against this Purchase Invoice for a company say 'Company XYZ' and link them together.

#### To create Inter Company Invoices as mentioned in the above process, you need to follow the below steps:

 - Go to the Customer list, select the customer which you would want to choose for the inter-linked invoices, enable the checkbox, **Is Internal Customer** as shown below:

 <img class="screenshot" alt="Internal Customer" src="{{docs_base_url}}/assets/img/accounts/make-internal-customer.png">

 - Along with that, add the company which the Customer represents, i.e. the company for which the Sales Invoice will be created.
 - Next, fill up the child table **Allowed To Transact With** as shown in the image and add the company against which you will be creating a Purchase Invoice, which will be linked with the Sales Invoice created  using this Customer.
 - *Easy peasy, right?* Now, you need to follow the similar procedure for setting up a Supplier for inter-linked invoices. And, in the **Represents Company** field, add the company which you added in the child table **Allowed To Transact With** for the Customer.
 - And, in the child table **Allowed To Transact With** for the Supplier, add the company which the Customer represents or against which you are going to make an inter-linked Purchase Invoice. You can refer the below image to avoid any confusion.

 <img class="screenshot" alt="Internal Supplier" src="{{docs_base_url}}/assets/img/accounts/make-internal-supplier.png">

- Now, create a new Sales Invoice, fill up the fields, and remember to select the Customer who is an internal customer and company which the Customer represents.
- Submit the Invoice.

 <img class="screenshot" alt="Inter company invoice" src="{{docs_base_url}}/assets/img/accounts/make-inter-company-invoice.png">

- Under the **Make** button dropdown, you will find a link **Inter Company Invoice**, on clicking the link, you will be routed to a new Purchase Invoice form page.
- Here, the supplier and company will be auto-fetched depending on the company you selected in the Sales Invoice. ***Remember**: There can only be a single Internal Supplier or Customer per company.*
- Submit the invoice, done! Now, both the invoices are inter-linked. *Also, on cancelling any of the invoices, the link will break as well.*

You can follow the same process to create a Purchase Invoice and then an inter-linked Sales Invoice from the submitted Purchase Invoice.

{next}