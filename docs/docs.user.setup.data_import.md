---
{
	"_label": "Data Import Tool"
}
---
The ￼Data Import Tool is a great way to upload (or edit) bulk data, specially master data, into the system. To start the tool go to:

> Setup > Data > Data Import Tool

The tool has two sections, one to download a template and the second to upload the data.

To upload any type of information, select a type from the drop-down. When you select, the system will give you one or more list of templates you can download. So why multiple templates?

In ERPNext, each master or transaction is defined by a “main table” and “child tables”. These child tables are there because some master tables could have multiple value of certain properties. For example, select Item. Here you will see a number of “child” tables linked to the item table. This is because an Item can have multiple prices, taxes and so on! You must import each table separately. In the child table, you must the mention the parent of the row in the “parent” column so that ERPNext knows which Item’s price or tax you are trying to set.

### The Template

Here is a few tips of filling out your template:

- Don’t change any cells before the row “----Start entering data below this line----”.
- Leave the first column blank.
- Read the explanations of the columns.
- Some columns are mandatory (the 5th row will tell you which ones those are).
- Columns of type “Link” and “Select” will only accept values from a certain set.
- For “Link” type columns, the value must be present in the table it links to.
- For “Select” the options are given on the 6th row. The value must be one of those.
- Dates: A number of standard date formats are accepted. Please make sure, your dates are in one of those formats.

### Overwriting

ERPNext also allows you to overwrite all / certain columns. If you want to update certain column, you can download the template with data and when you upload remember to check on the “Overwrite” box before uploading.

> Note: For child records, if you select Overwrite, it will delete all the child records of that parent.

### Upload Limitations

ERPNext restricts the amount of data you can upload in one file. Though the number may vary based on the type of data. It is usually safe to upload 100-200 rows of a table at one go. If the system will not accept, then you will see an error.

Why is this? Uploading a lot of data can cause your system to crash, specially if there are other users doing things in parallel. Hence ERPNext restricts the number of “writes” you can process in one request.
