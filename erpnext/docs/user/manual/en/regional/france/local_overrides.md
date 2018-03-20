# Sales and Payment Transactions

In order to be compliant with the latest finance law applicable to POS software, ERPNext automatically registers all sales and payment transactions in a chained log.

If your country is set to "France", the deletion of sales and payment transactions will also not be permitted, even if the appropriate permissions are given to the user.

Please note that ERPNext is not yet fully compliant with the 2016 Finance Law.

# Chained log Report

A dedicated report called "Transaction Log Report" is available to verify that the logged chain has not been broken.

If the status of the column "Chain Integrity" is "True", the chain has not been broken.
It means that you can consult the full chain of events that occurred in your system.

If the status of the column "Chain Integrity" is "False", it means that there is a discrepancy in the chain.
In this case, the previous row has been removed or altered in the database. It is a probable effect of a fraudulent behavior.
