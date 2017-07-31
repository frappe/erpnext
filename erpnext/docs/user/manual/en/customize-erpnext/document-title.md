# Document Title

You can customize the title of documents based on properties so that you have meaningful information for the list views.

For example the default title on **Quotation** is the customer name, but if you are dealing a few customers and sending lots of quotes to the same customer, you may want to customize.

#### Setting Title Fields

From ERPNext Version 6.0 onwards, all transactions have a `title` property. If there is not a title property, you can add a **Custom Field** as title and set the **Title Field** via **Customize Form**.

You can set the default value of that property by using Python style string formatting in **Default** or **Options**

To edit a default title, go to

1. Setup > Customize > Customize Form
2. Select your transaction
3. Edit the **Default** field in your forms

#### Defining Titles

You can define the title by setting document properties in braces `{}`. For example if your document has properties `customer_name` and `project` here is how you can set the default title:

    {customer_name} for {project}

<img class="screenshot" alt = "Customize Title"
    src="{{docs_base_url}}/assets/img/customize/customize-title.gif">

#### Fixed or Editable Titles

If your title is generated as a default title, it can be edited by the user by clicking on the heading of the document.

<img class="screenshot" alt = "Editable Title"
    src="{{docs_base_url}}/assets/img/customize/editable-title.gif">

If you want a fixed title, you can set the rule in the **Options** property. In this way, the title will be automatically updated everytime the document is updated.

{next}
