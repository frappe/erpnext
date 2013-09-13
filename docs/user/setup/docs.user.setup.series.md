---
{
	"_label": "Document Naming Series"
}
---
Data records are broadly classified as “Master” or “Transaction”. A master record is a record that has a “name”, for example a Customer, Item, Supplier, Employee etc. A Transaction is a record that has a “number”. Examples of transactions include Sales Invoices, Quotations etc. You make transactions against a number of master records.

ERPNext allows you to make prefixes to your transactions, with each prefix forming its own series. For example a series with prefix INV12 will have numbers INV120001, INV120002 and so on.

You can have multiple series for all your transactions. It is common to have a separate series for each financial year. For example in Sales Invoice you could have:

- INV120001
- INV120002
- INV-A-120002

etc. You could also have a separate series for each type of Customer or for each of your retail outlets.

To setup a series, go to:

> Setup > Tools > Update Numbering Series



![Document Naming Series](img/naming-series.png)



In this form,

1. Select the transaction for which you want to make the series
The system will update the current series in the text box.
1. Edit the series as required with unique prefixes for each series. Each prefix must be on a new line.
1. The first prefix will be the default prefix. If you want the user to explicitly select a series instead of the default one, check the “User must always select” check box.

You can also update the starting point for a series by entering the series name and the starting point in the “Update Series” section.