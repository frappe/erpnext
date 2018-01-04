# Request For Quotation

A Request for Quotation is a document that an organization submits to one or more suppliers eliciting quotation for items.

In ERPNext, You can create Request for Quotation directly by going to:

> Buying > Documents > Request for Quotation > New Request for Quotation

After creation of Request for Quotation, there are two ways to generate Supplier Quotation from Request for Quotation.


#### For User

__Step 1:__ Open Request for Quotation and click on make Supplier Quotation.

![Request For Quotation](/docs/assets/img/buying/make-supplier-quotation-from-rfq.png)

__Step 2:__ Select supplier and click on make Supplier Quotation.

![Request For Quotation](/docs/assets/img/buying/supplier-selection-from-rfq.png)

__Step 3:__ System will open the Supplier Quotation, user has to enter the rate and submit it.

![Request For Quotation](/docs/assets/img/buying/supplier-quotation-from-rfq.png)

#### For Supplier

__Step 1:__ User has to create contact or enter Email Address against the supplier on Request for Quotation.

![Request For Quotation](/docs/assets/img/buying/set-email-id.png)

__Step 2:__ User has to click on send supplier emails button.

* If supplier's user not available: system will create supplier's user and send details to the supplier, supplier will need to click on the link(Password Update) present in the email. After password update supplier can access his portal with the Request for Quotation form.

![Request For Quotation](/docs/assets/img/buying/supplier-password-update-link.png)

* If supplier's user available: system will send Request for Quotation link to supplier, supplier has to login using his credentials to view Request for Quotation form on portal. 

![Request For Quotation](/docs/assets/img/buying/send-rfq-link.png)

__Step 3:__ Supplier has to enter amount and notes(payment terms) on the form and click on submit

![Request For Quotation](/docs/assets/img/buying/supplier-portal-rfq.png)

__Step 4:__ On submission, system will create Supplier Quotation (draft mode) against the supplier. The user has to review the Supplier Quotation
            and submit it. When all items from the Request for Quotation have been quoted by a supplier, the status is updated in the Supplier 
			table of the Request for Quotation.

#### More details

If a supplier indicates that they will not provide a quotation for the item, this can be indicated in the RFQ document by checking the 'No Quote' box after the Request for Quotation has been submitted.

![Request For Quotation](/docs/assets/img/buying/request-for-quotation.gif)
