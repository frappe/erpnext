Custom Field feature allows you to insert fields in the existing masters and transactions as per your requirement. While inseting custom field, you can define its properties like.

* Field Name/Label
* Field Type
* Mandatory/Non-Mandatory
* Insert After Field

To add a Custom Field, go to:

> Setup > Customize > Custom Field > New Custom Field

You can also insert new Custom Field from [Customize Form](https://erpnext.com/customize-erpnext/customize-form) tool.

In Customize Form, for each field, you will find plus (+) option. When click on it, new row will be inserted above that field. You can enter properties for your Custom Field in the newly added blank row.

![Customize Form Custom Field]({{docs_base_url}}/assets/old_images/erpnext/customize-form-custom-field.png)

Following are the steps to insert Custom Field in the existing form.

####New Custom Field form / Row in Customize Form

As mentioned above, you can insert Custom Field from Custom Field form, and also from Customize Form.

####Select Document/Form

You should select transaction or master in which you want to insert custom field. Let's assume you need to insert a custom link field in the Quotation form. In this case, Document will be "Quotation".

![Custom Field Document]({{docs_base_url}}/assets/old_images/erpnext/custom-field-document.png)

####Set Field Label

Custom Field's name will be set based on its Label. If you want to create Custom Field with specific name, but with different label, then you should first set Label as you want Field Name to be set. After Custom Field is saved, you can edit the Field Label again.

![Custom Field Label]({{docs_base_url}}/assets/old_images/erpnext/custom-field-label.png)

####Select Insert After

This field will have all the existing field of the form/doctype selected. Your Custom Field will be placed after field you select in the Insert After field.

![Custom Field Insert]({{docs_base_url}}/assets/old_images/erpnext/custom-field-insert.png)

####Select Field Type

Click [here](https://erpnext.com/kb/customize/field-types) to learn more about types of field you can set for your Custom Field.

![Custom Field Type]({{docs_base_url}}/assets/old_images/erpnext/custom-field-type.png)

####Set Option

If you are creating a Link field, then Doctype name with which this field will be linked to will be entered in the Option field. Click [here](https://erpnext.com/kb/customize/creating-custom-link-field) to learn more about creating custom link field.

![Custom Field Link]({{docs_base_url}}/assets/old_images/erpnext/custom-field-link.png)

If field type is set as Select (drop down field), then all he possible result for this field should be listed in the Options field. Each possible result should be separate by row.

![Custom Field Option]({{docs_base_url}}/assets/old_images/erpnext/custom-field-option.png)

For other field types, like Data, Date, Currency etc., Opton field will be left blank.

####Set More Properties

You can set properties as:

1. Mandatory: Should this field be mandatory or non-mandatory.
1. Print Hide: Should this field be visible in the print format or no.
1. Field Description: It will be short field description which will appear just below that field.
1. Default Value: Value entered in this field will be auto-updated in this field.
1. Read Only: Checking this option will make custom field non-editable.
1. Allow on Submit: Checking this option will allow editing value in the field when in submitted transaction.

![Custom Field Properties]({{docs_base_url}}/assets/old_images/erpnext/custom-field-properties.png)

####Deleting Custom Field

Given a permission, user will be able to delete Custom Fields. Incase, it was deleted by default, if you add another Custom Field with same name. Then you shall see new field auto-mapped with old-deleted Custom Field.

{next}
