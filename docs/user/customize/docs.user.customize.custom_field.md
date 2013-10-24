---
{
	"_label": "Custom Field"
}
---
A very common customization is adding of custom fields. You can add Custom Fields in any Master or Transaction in ERPNext. To add a Custom Field, go to:

> Setup > Custom Field > New Custom Field

![Custom Field](img/custom-field.png)



In the form:

- Select the Document on which you want to add the Custom Field.
- Select the Type of field and the Options .
- Select where you want the field to appear in the Form (“after field” section).

and save the Custom Field. When you open a new / existing form of the type you selected in step 1, you will see it with the Custom Fields.

To understand Custom Fields in detail, visit [DocType-Fields](docs.user.knowledge.doctype_fields.html)

#### Naming

Many times you want your fields to be carried over from one form to another. For example, you may have added a Custom Field in Quotation that you want to include in Sales Order when a Sales Order is created from the Quotation. This is simple in ERPNext, just make sure the fields have the same “fieldname”
