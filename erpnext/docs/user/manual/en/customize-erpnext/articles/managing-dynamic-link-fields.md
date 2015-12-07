<h1>Managing Dynamic Link Fields</h1>

Dynamic Link field is one which can search and hold value of any document/doctype. Let's consider an example to learn how Dynamic Link field can benefit us.

While creating Opportunity or Quotation, we have to explicitly define if it is for Lead or Customer. Based on our selection (Lead/Customer), another link field shows up where we can select actual Lead or Customer for whom we are creating this Quotation.

If you set later field as Dynamic Link, where we select actual Lead or Customer, this field will be able to search Leads as well as Customers. Hence we need not insert separate link fields for Customer and Lead.

Let's check steps to insert Custom Dynamic Field. For an instance, we will insert it under Journal Voucher Form.

####Insert Link Field for Doctype

Firstly we will create a link field which will be linked to the Doctype.

![Custom Link Field]({{docs_base_url}}/assets/img/articles/$SGrab_349.png)

By **Doctype** mentioned in the Option field, we mean parent Doctype. So, just like Quotation is one Doctype, which has multiple Quotation under it. Same way, Doctype is also a Doctype which has Sales Order Doctype, Purchase Order Doctype and other form's doctype created under it as child Doctype.

-- Doctype<br>
----- Sales Order<br>
----- Purchase Invoice<br>
----- Quotation<br>
----- Sales Invoice<br>
----- Employee<br>
----- Production Order<br>
and so on, till all the forms/document of ERPNext is covered.

So linking this field with parent Doctype master list all the child doctypes/forms.

![journal Voucher Link Field]({{docs_base_url}}/assets/img/articles/$SGrab_352.png)

####Insert Dynamic Link Field

It will be "Dynamic Link" for Field Type, and field name of Doctype field mentioned in its Option field.

![Custom Dynamic Field]({{docs_base_url}}/assets/img/articles/$SGrab_350.png)

This field will allow us to select document id, based on value selected in the Doctype link field. For example, if we select Sales Order in the prior field, this field will list all the Sales Orders id. If we select Purchase Invoice in the prior field, this field will render all the Purchase Order for our selection.

![Journal Voucher Dynamic Field ]({{docs_base_url}}/assets/img/articles/$SGrab_353.png)

####Customizing options in the Doctype Link field

Bydefault, Docytpe link field will provide all the forms/doctypes for selection. If you wish this field to show certain specific doctypes in the search result, you will need to write Custom Script for it.

<!-- markdown -->