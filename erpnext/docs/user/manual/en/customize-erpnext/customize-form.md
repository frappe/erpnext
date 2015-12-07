<!--markdown-->
Before we venture to learn form customization tool, click [here](https://kb.frappe.io/kb/customization/form-architecture) to understand the architecture of forms in ERPNext. It shall help you in using Customize Form tool more efficiently.

Customize Form is the tool which allows user to customize the property of standard fields as per the requirement. Let's assume we need to set Project Name field as mandatory in the Sales Order form. Following are the steps which shall be followed to achieve this.

####Step 1: Go to Customize Form

You can go to Customize Form from:

> Setup >> Customize >> Customize Form

System Manager will find Customize Form option in the Sales Order list (or any other form for that matter) view as well.

![Customize Form List View]({{docs_base_url}}/assets/old_images/erpnext/customize-form-list-view.png)

####Step 2: Select Docytpe/Document

You should select Docytpe/Document which has field-to-be-customized located in it.

![Customize Form Document]({{docs_base_url}}/assets/old_images/erpnext/customize-form-document.png)

####Step 3:Edit Property

On selecting Doctype/table, you will have all the fields of the table updated as rows in the Customize Form table. You should drill down to field you need to work on, Project Name in this case.

On clicking Project Name row, fields to set various property for this field will be shown. To Customize the mandatory property for a field, there is a field called "Mandatory". Checking this field will set Project Name field as mandatory in the Quotation form.

![Customize Form Mandatory]({{docs_base_url}}/assets/old_images/erpnext/customize-form-mandatory.png)

Like this, you can customize following properties of the field.

* Change field types (for e.g. you want to increase the number of decimal places, you can convert come fields from Float to Currency).
* Change labels to suit your industry / language.
* Make certain fields mandatory.
* Hide certain fields.
* Change layout (sequence of fields). To do this, select a field in the grid and click on“Up” or “Down” in the grid toolbar.
* Add / edit “Select” Options. (for example, you can add more sources in Leads etc).

####Step 4: Update

![Customize Form Update]({{docs_base_url}}/assets/old_images/erpnext/customize-form-update.png)

Before checking Sales Order form, you should clear cache and refresh browser tab for customization to take effect.

For Customize Form, you can also allow attachments, set max number of attachments and set the default Print Format.

>Note: Though we want you to do everything you can to customize your ERP based on your business needs, we recommend that you do not make “wild” changes to the forms. This is because, these changes may affect certain operations and may mess up your forms. Make small changes and see its effect before doing some more.

Following are the properties which you can customize for a specific field from Customize Form.
<style>
    td {
    padding:5px 10px 5px 5px;
    };
    img {
    align:center;
    };
table, th, td {
    border: 1px solid black;
    border-collapse: collapse;
}
</style>
<table border="1" width="700px">
  <tbody>
    <tr>
      <td style="text-align: center;"><b>Field property</b></td>
      <td style="text-align: center;"><b>Purpose</b></td>
    </tr>
    <tr>
      <td>Print hide</td>
      <td>Checking it will hide field from Standard print format.</td>
    </tr>
    <tr>
      <td>Hidden</td>
      <td>Checking it field will hide field in the data entry form.</td>
    </tr>
    <tr>
      <td>Mandatory</td>
      <td>Checking it will set field as mandatory.</td>
    </tr>
    <tr>
      <td>Field Type</td>
      <td>Click <a href="https://erpnext.com/kb/customize/field-types">here</a> to learn about of fields types.</td>
    </tr>
    <tr>
      <td>Options</td>
      <td>Possible result for a drop down fields can be listed here. Also for a link field, relevant Doctype can be provided.</td>
    </tr>
    <tr>
      <td>Allow on submit</td>
      <td>Checking it will let user update value in field even in submitted form.</td>
    </tr>
    <tr>
      <td>Default</td>
      <td>Value defined in default will be pulled on new record creation.</td>
    </tr>
    <tr>
      <td>Description</td>
      <td>Gives field description for users understanding.</td>
    </tr>
    <tr>
      <td>Label</td>
      <td>Label is the field name which appears in form.</td>
    </tr>
  </tbody>
</table>

{next}
