# Customizing visibility of data in the child table

**Question:** Currently, in the child table (like Item table in Quotation), we can view value in the four columns only. How can we have more values previewed in the child table?

**Answer:** In the version 7, we introduced a feature, editable grid. This allowed the user to add values in the child table without opening dialog box/form for each row.

This is how Quotation Item table renders value when Editable Grid is enabled. It will maximum list four columns in the table.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/child-1.png">

As per the default setting, only four columns are listed in the child table. Following is how you can add more columns in the editable itself.

For the field to be added as a column in the table, enter a value in the Column field. Also, ensure that "Is List View" property is checked for that field.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/child-2.png">

Based on the value in the Column field, columns will be added in the child table. Ensure that sum total of value added in the Column field doesn't exceed 10. Based on the Column value, width for that column will be set.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/child-3.png">

**Switch to Un-editable Grid**

To have more values shown in the preview of Quotation Item table, you can disable Editable Grid for the Quotation Item Doctype. Steps below.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/child-4.gif">

Once Editable Grid is disabled for the Quotation Item, the following is how values will be rendered in a preview of the Quotation Item table.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/child-5.png">

To have specific field's value shown in the preview, ensure that for that field, in the Customize Form tool, "In List View" property is checked.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/child-6.png">