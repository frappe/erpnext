# Customize Form

<!--markdown-->
Before we venture to learn form customization tool, click [here](https://frappe.io/docs/user/en/tutorial/doctypes.html) to understand the architecture of forms in ERPNext. It shall help you in using Customize Form tool more efficiently.

Customize Form is the tool which allows user to customize property of the standard fields, and insert [custom fields](/docs/user/manual/en/customize-erpnext/custom-field.html) as per the requirement. Let's assume we need to set Project Name field as a mandatory field in the Sales Order form. Following are the steps which shall be followed to achieve this.

####Step 1: Go to Customize Form

Go to Customize Form from:

`Setup >> Customize >> Customize Form`

You can also reach the Customize Form tool from the List Views.

<img alt="Customize Form List" class="screenshot" src="/docs/assets/img/customize/customize-form-from-list-view.gif">

####Step 2: Select Document Type

If navigate from the list view, Document Type will be automatically set in the Customize Form.

If you reach customize form from the Setup module, or from awesome bar, then you will have to manually select Document Type in which customization needs to be made.

<img alt="Customize Form select doctype" class="screenshot" src="/docs/assets/img/customize/customize-form-select-doctype.png">

####Step 3: Edit Property

On selecting Document Type, all the fields of the Document Type will updated as rows in the Customize Form.

To customized Project field, click on the respective row, and check "Mandatory". With this, Project field will become mandatory in the Sales Order.

<img alt="Customize Form select doctype" class="screenshot" src="/docs/assets/img/customize/customize-form-edit-property.gif">

Like setting setting field Mandatory, following are the other customization options in the Customize Form tool.

* Change [Field Type](/docs/user/manual/en/customize-erpnext/articles/field-types.html).
* Edit Field Labels to suit your industry/language.
* Set field precision for the Currency field.
* To hide field, check Hidden.
* Customize Options for the Select field.

####Step 4: Update

To save your customizations, Update Customize Form.

To have customizations take effect, reload your ERPNext account once.

####Other Customizations

From Customize Form, you can also do following customizations:

* Max Attachment Limit: Define [maximum no. of files](/docs/user/manual/en/customize-erpnext/articles/increase-max-attachments.html) which can attached on a document.
* Default Print Format: For one document type, you can have multiple print formats. In the Customize Form, you can also set default Print Format for a document.
* Set [Title Field](/docs/user/manual/en/customize-erpnext/document-title.html)
* Sort Field and Sort Order: Define field based on which documents in the list view will be sorted.

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
      <td>Checking it will hide field from the Standard print format.</td>
    </tr>
    <tr>
      <td>Unique</td>
      <td>For a unique field, same value cannot repeat in another document.</td>
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
      <td>Click <a href="/docs/user/manual/en/customize-erpnext/articles/field-types.html">here</a> to learn about of fields types.</td>
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
