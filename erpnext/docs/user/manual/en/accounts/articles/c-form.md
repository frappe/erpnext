# C Form

#C-Form

C-Form functionality is only applicable for Indian customers.

**What is C-Form?**

C-Form is issued by the Customer. If Customer Issues C-Form, supplier applies discounted CST (central sales tax) in the invoice. C-Form is only applicable on the inter-state transactions.

C-Form functionality in ERPNext allows Supplier to update C-Form No. as received from Customer in the submitted Sales Invoice. Also you can create report on Sales Invoice and track invoices for which C-Form has not yet been received from Customer.

Following are step to manage C-Form related sales in ERPNext.

####Set C-Form Applicability

While creating Sales invoice for the customer, set C-Form applicability in Sales Invoice. In More Info section of Sales Invoice, set field called **Is C-Form Applicable** as **Yes**. Bydefault, this field will have No for a value.
 
![C-form]({{docs_base_url}}/assets/img/articles/Selection_0028c9f9a.png)

Updating this field as Yes will allow you to pull this Sales Invoice in the C-Form Tool, and update C-Form No. as received from the Customer.

####Create C-Form Record

After receiving C-Form from your Customer, you should update that C-Form no. in the Sales Invoice by creating C-Form record.

Go to `Accounts > Setup > C-Form > New`

Enter details like C-Form No, Received Date, State and Amount etc. Select Customer and pull related Sales Invoices under provided table.

![New C-Form]({{docs_base_url}}/assets/img/articles/Selection_020f01c1e.png)

####Save & Submit C-Form

After entering details, save and submit C-Form record. On save system will generate C-Form record and on submission update that C-Form No. in the Sales Invoice.

![C-Form]({{docs_base_url}}/assets/img/articles/Selection_02178f9d6.png)

C-Form serial no will be updated in related invoice under the field 'C-Form No'.

![C-Form No]({{docs_base_url}}/assets/img/articles/Selection_022b7c6d5.png)

####Tracking Pending Invoice for C-Form

To track invoices for which C-Form has not yet been received from Customer, you can create custom report on Sales Invoice. In this report, you can filter invoices which doesn't have C-Form updated in them yet, and followup with the customer accordingly.

![C-Form Report]({{docs_base_url}}/assets/img/articles/Selection_026.png)

<!-- markdown -->
