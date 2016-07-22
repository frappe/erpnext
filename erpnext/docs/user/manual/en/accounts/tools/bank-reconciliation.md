### Bank Reconciliation Statement

If you are receiving payments or making payments via cheques, the bank statements will not accurately match the dates of your entry, this is because the bank usually takes time to “clear” these payments. Also you may have
mailed a cheque to your Supplier and it may be a few days before it is received and deposited by the Supplier. In ERPNext you can synchronise your bank statements and your Journal Entrys using the “Bank Reconciliation”
tool.

The Bank Reconciliation Report provide the difference between the bank balance shown in an organisation's bank statement, as provided by the ban against amount shown in the companies Chart of Accounts.

####Bank Reconciliation Statement

![]({{docs_base_url}}/assets/old_images/erpnext/bank-reconciliation-2.png)  

In the report, check whether the field 'Balance as per bank' matches the Bank Account Statement. If it is matching, it means that Clearance Date is correctly updated for all the bank entries. If there is a mismatch, Its because of bank entries for which Cleanrane Date is not yet updated.

To add clearance entries go to:

> Accounts > Tools > Bank Reconciliation

###Bank Reconciliation Tool

o use this, go to:

> Accounts > Tools > Bank Reconciliation

Select your “Bank” Account and enter the dates of your statement. Here you
will get all the “Bank Voucher” type entries. In each of the entry on the
right most column, update the “Clearance Date” and click on “Update”.

By doing this you will be able to sync your bank statements and entries into
the system.

__Step 1:__ Select the Bank Account against which you intend to reconcile. For
example; HDFC Bank, ICICI Bank, or Citibank etc.

__Step 2:__ Select the Date range that you wish to reconcile for.

__Step 3:__ Click on 'Get Reconciled Entries'

All the entries in the specified date range will be shown in a table below.

__Step 4:__ Click on the JV from the table and update clearance date.

<img class="screenshot" alt="Bank Reconciliation" src="{{docs_base_url}}/assets/img/accounts/bank-reconciliation.png">

__Step 5:__ Click on the button 'Update Clearance Date'.
 
{next}
