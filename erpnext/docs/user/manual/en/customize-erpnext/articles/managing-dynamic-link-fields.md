#Managing Dynamic Link Fields

Dynamic Link field is one which can search and hold value of any document/doctype. Let's consider an example to learn how Dynamic Link field works.

While creating Opportunity or Quotation, we have to explicitly define if it is for Lead or Customer. Based on our selection (Lead/Customer), another link field shows up where we can select actual Lead or Customer.

If you set former field as Dynamic Link, where we select actual Lead or Customer, then the later field will be linked to master selected in the first field, i.e. Leads or Customers. Hence we need not insert separate link fields for Customer and Lead.

Below are the steps to insert Custom Dynamic Field. For an instance, we will insert Dynamic Link Field in Journal Entry.

#### Step 1: Insert Link Field for Doctype

Firstly we will create a link field which will be linked to the Doctype.

<img alt="Custom Link Field" class="screenshot" src="/docs/assets/img/articles/dynamic-field-1.gif">

By **Doctype** mentioned in the Option field, we mean parent Doctype. So, just like Quotation is one Doctype, which has multiple Quotation under it. Same way, Doctype is also a Doctype which has Sales Order, Purchase Order and other doctypes created as Doctype records.

-- Doctype<br>
---- Sales Order<br>
---- Purchase Invoice<br>
---- Quotation<br>
---- Sales Invoice<br>
---- Employee<br>
---- Production Order<br>
.. and so on.

So linking this field with parent Doctype will list all the Doctype records.

<img alt="journal Voucher Link Field" class="screenshot" src="/docs/assets/img/articles/dynamic-field-2.png">

#### Step 2: Insert Dynamic Link Field

This custom field's type will be "Dynamic Link". In the Option field, name of Doctype link field will be mentioned.

<img alt="Custom Dynamic Field" class="screenshot" src="/docs/assets/img/articles/dynamic-field-3.gif">

This field will allow selecting document id, based on value selected in the Doctype link field. For example, if we select Sales Order in the prior field, Dynamic Link field will list all the Sales Orders ids.

<img alt="Custom Dynamic Field" class="screenshot" src="/docs/assets/img/articles/dynamic-field-4.gif">

<div class="well">
**Customizing options in the Doctype Link field**

By default, Docytpe link field will provide all the forms/doctypes for selection. If you wish this field to show certain specific doctypes in the search result, you will need to write Custom Script for it.
</div>

<!-- markdown -->
