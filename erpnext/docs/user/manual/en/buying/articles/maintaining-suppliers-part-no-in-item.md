<h1>Maintaining Supplier's Item Code in the Item master</h1>

Since each company has their own item coding standards, for each item, your item code differ from supplier's Item Code. ERPNext allows you to track Supplier's Item Code in your item master, so that you refer to each others item code while transacting. Also you can fetch Supplier's Item Code in your purchase transactions, so that they can easily recognize item referring to their Item Code.

#### 1. Updating Supplier Item Code In Item

Under Purchase section in the Item master, you will find table to track Item Code for each Supplier.

![Item Supplier Item Code]({{docs_base_url}}/assets/img/articles/Supplier Item Code.png)

#### 2. Supplier's Item Code in Transactions

Each purchase transaction has field in the Item table where Supplier's Item Code is fetched. This field is hidden in form as well as in the Standard print format. You can make it visible by changing property for this field from [Customize Form](https://erpnext.com/user-guide/customize-erpnext/customize-form).

Supplier Item Code will only be fetched in the purchase transaction, if both Supplier and Item Code selected in purchase transaction is mapped with value mentioned in the Item master.

![Supplier Item Code in transaction]({{docs_base_url}}/assets/img/articles/Supplier Item Code in Purchase Order.png)


<!-- markdown -->