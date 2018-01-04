# Custom Field

Every form in the ERPNext has standard set of fields. If you need to capture some information, but there is no standard field available for it, you can insert Custom Field in a form as per your requirement.

Following are the steps to insert Custom Field in the existing form.

####Customize Form

To add a Custom Field, go to:

`Setup > Customize > Customize Form`

####Select Document Type

In the Customize Form, select Document Type in which you want to insert Custom Field. Let's assume we are inserting Custom Field in the Employee master.

<img alt="Select Document Type" class="screenshot" src="/docs/assets/img/customize/custom-field-1.gif">

#### Insert Row for the Custom Field

In Customize Form, open the field above which you want to insert a Custom Field. Click on Insert Above.

<img alt="Select Document Type" class="screenshot" src="/docs/assets/img/customize/custom-field-2.gif">

####Set Field Label

Custom Field's name will be set based on its Label. If you want to create Custom Field with specific name, but with different label, then you should first set Label as you want Field Name to be set. After Custom Field is saved, you can edit the Field Label again.

<img alt="Select Document Type" class="screenshot" src="/docs/assets/img/customize/custom-field-3.png">

####Select Field Type

There are various types of Field like Data, Date, Link, Select, Text and so on. Select Field Type for the Custom Field.

<img alt="Select Document Type" class="screenshot" src="/docs/assets/img/customize/custom-field-4.png">

Click [here](/docs/user/manual/en/customize-erpnext/articles/field-types.html) to learn more about types of field you can set for your Custom Field.

####Set Option

Based on the Field Type, value will be entered in the Options field.

If you are creating a Link field, then in the Options, enter Doctype name with which this field will be linked. Click [here](/docs/user/manual/en/customize-erpnext/articles/creating-custom-link-field.html) to learn more about creating custom link field.

If field type is set as Select (drop down field), then all he possible result for this field should be listed in the Options field. Each possible result should be separate by row.

<img alt="Select Document Type" class="screenshot" src="/docs/assets/img/customize/custom-field-5.png">

For Data field, Option can be set to "Email" or "Phone" and the field will be validated accordingly.

For other field types like Date, Currency, Option field will be left blank.

####Set More Properties

You can set properties as:

1. Mandatory: If checked, entering data in the custom field will be mandatory.
1. Print Hide: If checked, this field will be hidden from the Standard Print Format. To make field visible in the Standard Print Format, uncheck this field.
1. Field Description: It will be short field description which will appear just below that field.
1. Default Value: Value entered in this field will be auto-set in the Custom Field.
1. Read Only: Checking this option will make custom field non-editable.
1. Allow on Submit: Checking this option will allow editing value in the field when in submitted transaction.

####Update Customize Form

After inserting required details for the Custom Field, Update Customize Form. On update, Custom Field will be inserting in the form, Employee master in this case. Before checking Employee form, reload your ERPNext account. After reload, check Employee form to see Custom Field in a form.

<img alt="Select Document Type" class="screenshot" src="/docs/assets/img/customize/custom-field-6.png">

####Deleting Custom Field

Given a permission, user will be able to delete Custom Fields. Incase Custom Field is deleted by mistake, if you add another Custom Field with same name. Then you shall see new field auto-mapped with old-deleted Custom Field.

{next}
