#Field Types

Following are the types of fields you can define while creating new ones, or while amend standard ones.

- Attach: 

Attach field allows you browsing file from File Manager and attach in the transaction.

- Button: 

It will be a Button, on clicking which you can execute some functions like Save, Submit etc. 

- Check:

It will be a check box field. 

- Column Break

Since ERPNext has multiple column layout, using Column Breaks, you can divide set of fields side-by-side. 

- Currency

Currency field holds numeric value, like item price, amount etc. Currency field can have value upto six decimal places. Also you can have currency symbol being shown for the currency field.

- Data

Data field will be simple text field. It allows entering value upto 255 characters.

- Date and Time

This field will give you date and time picker. Current date and time (as provided by your computer) is set by default. 

- Dynamic Link

Click [here](/docs/user/manual/en/customize-erpnext/articles/managing-dynamic-link-fields.html) to learn how Dynamic Link Field function.

- Float

Float field carries numeric value, upto six decimal place. Precision for the float field is set in
 
`Setup > Settings > System`

Setting will be applicable on all the float field. 

- Image

Image field will render an image file selected in another attach field. 

For the Image field, under Option (in Doctype),field name should be provide where image file is attached. By referring to the value in that field, image will be reference in the Image field.

- Int (Integer)

Integer field holds numeric value, without decimal place.

- Link

Link field is connected to another master from where it fetches data. For example, in the Quotation master, Customer is a Link field.

- Password

Password field will have decode value in it.

- Read Only

Read Only field will carry data fetched from another form, but they themselves will be non-editable. You should set Read Only as field type if its source for value is predetermined.

- Section Break

Section Break is used to divide form into multiple sections. 

- Select

Select will be a drop-down field. You can add muliple results in the Option field, separated by row.

- Small Text

Small Text field carries text content, has more character limit than the Data field.

- Table

Table will be (sort of) Link field which renders another docytpe within the current form. For example, Item table in the Sales Order is a Table field, which is linked to Sales Order Item doctype.

- Text Editor

Text Editor is text field. It has text-formatting options. In ERPNext, this field is generally used for defining Terms and Conditions.

<!-- markdown -->