# Supplier

Suppliers are companies or individuals who provide you with products or services.

You can create a new Supplier from:

`Explore > Supplier > New Supplier`

<img class="screenshot" alt="Supplier Master" src="/docs/assets/img/buying/supplier-master.png">

### Contacts and Addresses

Contacts and Addresses in ERPNext are stored separately so that you can create multiple Contacts and Addresses for a Suppliers. Once Supplier is saved, you will find option to create Contact and Address for that Supplier.

<img class="screenshot" alt="Supplier Master" src="/docs/assets/img/buying/supplier-new-address-contact.png">

> Tip: When you select a Supplier in any transaction, Contact for which "Is Primary" field id checked, it will auto-fetch with the Supplier details.

### Integration with Accounts

For all the Supplier, "Creditor" account is set as default payable Account. When Purchase Invoice is created, payable towards the supplier is booked against "Creditors" account.

If you want to customize payable account for the Supplier, you should first add a payable Account in the Chart of Account, and then select that Payable Account in the Supplier master.

<img class="screenshot" alt="Supplier Master" src="/docs/assets/img/buying/supplier-payable-account.png">

If you don't want to customize payable account, and proceed with default payable account "Creditor", then do not update any value in the Default Supplier Account's table.

> Advanced Tip: Default Payable Account is set in the Company master. If you want to set another account as Account as default for payable instead of Creditors Account, go to Company master, and set that account as "Default Payable Account".

You can add multiple companies in your ERPNext instance, and one Supplier can be used across multiple companies. In this case, you should define Companywise Payable Account for the Supplier in the "Default Payable Accounts" table.

<iframe width="660" height="371" src="https://www.youtube.com/embed/anoGi_RpQ20" frameborder="0" allowfullscreen></iframe>

(Check from 2:20)

{next}
