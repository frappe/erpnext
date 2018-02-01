# Payment Terms
You can save your business' payment terms on ERPNext and include it in all documents in the sales/purchase cycle and ERPNext will make all the proper general ledger entries accordingly.

The documents you can attach Payment Terms to are:
- Sales Invoice
- Purchase Invoice
- Sales Order
- Purchase Order
- Quotation

Note that the introduction of Payment Terms removes "Credit Days" and "Credit Days Based On" fields in Customer/Supplier master. Payment Term contains the same information and makes it more flexible to use.

## Payment Terms
Navigate to the Payment Term list page and click "New".
> Accounts > Payment Term > New Payment Term

Payment Term has the following fields:
**Payment Term Name:** (optional) The name for this Payment Term.

**Due Date Based On:** The basis by which the due date for the Payment Term is to be calculated. There are three options:
- Day(s) after invoice date: Due date should be calculated in days with reference to the posting date of the invoice
- Day(s) after the end of the invoice month: Due date should be calculated in days with reference to the last day of the month in which the invoice was created
- Month(s) after the end of the invoice month: Due date should be calculated in months with reference to the last day of the month in which the invoice was created

**Invoice Portion:** (optional) The portion of the total invoice amount for which this Payment Term should be applied. Value given will be regarded as percentage i.e 100 = 100%

**Credit Days:** (optional) The number of days or month credit is allowed depending on the option chosen in the `Due Date Based On` field. 0 means no credit allowed.

**Description:** (optional) A brief description of the Payment Term.

## Payment Terms In Converted Documents
When converting or copying documents in the sales/purchase cycle, the attached Payment Term(s) will not be copied. The reason for this is because the copied information might no longer be true. For example, a Quotation is created for a service costing $1000 on January 1 with payment term of "N 30" (Net payable within 30 days) and then sent to a customer. On the quotation, the due date on the invoice will be January 30. Let's say the customer agrees to the quotation of January 20 and you decide to make an invoice from the Quotation. If the Payment Terms from the Quotation is copied, the due date on the invoice will still wrongly read January 30. This issue also applies for recurring documents.

This does not mean you have manually set Payment Terms for every document. If you want the Payment Terms to be copyable, make use of Payment Terms Template.

##  Payment Terms Template
Payment Terms Template tells ERPNext how to populate the table in the Payment Terms Schedule section of the sales/purchase document.
 
You should use it if you have a set of standard Payment Terms or if you want the Payment Term(s) on a sales/purchase document to be copyable.

To create a new Payment Terms Template, navigate to the Payment Term Template creation form:
> Accounts > Payment Terms Template > New Payment Terms Template

**Payment Term:** (optional) The name for this Payment Term.

**Due Date Based On:** The basis by which the due date for the Payment Term is to be calculated. There are three options:
- Day(s) after invoice date: Due date should be calculated in days with reference to the posting date of the invoice
- Day(s) after the end of the invoice month: Due date should be calculated in days with reference to the last day of the month in which the invoice was created
- Month(s) after the end of the invoice month: Due date should be calculated in months with reference to the last day of the month in which the invoice was created

**Invoice Portion:** (optional) The portion of the total invoice amount for which this Payment Term should be applied. Value given will be regarded as percentage i.e 100 = 100%

**Credit Days:** (optional) The number of days or month credit is allowed depending on the option chosen in the `Due Date Based On` field. 0 means no credit allowed.

**Description:** (optional) A brief description of the Payment Term.

Add as many rows as needed but make sure that the sum of the values in the `Invoice Portion` fields in all populated rows equals 100.

## How to Add Payment Terms To Documents
You can add Payments Terms in the "Payment Terms Schedule" section of the Document. Each row in the table represents a portion of the document's grand total. The table collects the following information:

**Payment Term:** (optional) The name of the Payment Term document you require. If this is added, the data from the selected Payment Term will be used to populate the remaining columns in the row.

**Description:** (optional) Description of the Payment Term.

**Due Date:** (optional) The due date for the portion of the invoice. Set this value only if you did not specify anything in the `Payment Term` column.

**Invoice Portion:** The percentage portion of the document represented in each row.

**Payment Amount:** The amount due from the portion of the invoice represented by each row.
