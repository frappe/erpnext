#Editing Value in Submitted Document

Once document is submitted, fields are frozen, and no editing is allowd. Still there are certain standard fields like Letter Head, Print Heading which can still be edited. For the custom field, if **Allow on Submit** property is checked, it will be editable even after document is submitted.

<div class="well"> Standard fields cannot be set as Allow on Submit.</div>

#### Step 1: Go To

`Setup > Customize > Customize Form`

####Step 2: Select Form

In Customize Form, select Document Type (Quotation, Sales Order, Purchase Invoice Item etc.)

<img alt="select docytpe" class="screenshot" src="{{docs_base_url}}/assets/img/articles/allow-on-submit-1.png">

#### Step 3: Edit Field Property

In the fields section, click on the Custom field and check the **Allow On Submit**.

<img alt="Check Allow on Submit" class="screenshot" src="{{docs_base_url}}/assets/img/articles/allow-on-submit-2.png">

#### Step 3: Update Customize Form

<img alt="Update" class="screenshot" src="{{docs_base_url}}/assets/img/articles/allow-on-submit-3.png">

After updating Customize Form, you should reload your ERPNext account. Then check form, and field to confirm its editable in submitted form as well.

<!-- markdown -->
