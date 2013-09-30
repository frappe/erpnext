---
{
	"_label": "DocType"
}
---



ERPNext is a based on a “metadata” (data about data) framework that helps define all the different types of documents in the system. The basic building block of ERPNext is a DocType. 

A DocType represents both a table in the database and a form from which a user can enter data. 

Many DocTypes are single tables, but some work in groups. For example, Quotation has a “Quotation” DocType and a “Quotation Item” doctype for the Items table, among others.  DocTypes contain a collection of fields called DocFields that form the basis of the columns in the database and the layout of the form.

<table class="table table-bordered text-left">
    <thead>
        <tr class="active">
            <td width="30%">Column</td>
            <td>Description</td>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Name</td>
            <td>Name of the record</td>
           
        </tr>
        <tr>
            <td>Owner</td>
            <td>Creator and Owner of the record</td>
          
        </tr>
        <tr>
            <td>Created on</td>
            <td>Date and Time of Creation</td>
          
        </tr>
        <tr>
            <td>Modified On </td>
            <td>Date and Time of Modification</td>
        </tr>
        <tr>
            <td>Docstatus</td>
            <td>Status of the record<br>
                0 = Saved/Draft<br>
                1 = Submitted<br>
                2 = Cancelled/Deleted
            </td> 
        </tr>
        <tr>
            <td>Parent</td>
            <td>Name of the Parent</td>
        </tr>
        <tr>
            <td>Parent Type</td>
            <td>Type of Parent</td>
        </tr>
        <tr>
            <td>Parent Field</td>
            <td>Specifying the relationship with the parent (there can be multiple child relationships with the same DocType).</td>
        </tr>
        <tr>
            <td>Index(idx)</td>
            <td>Index (sequence) of the record in the child table.</td>

        </tr>
    </tbody>
</table>

#### Single DocType

There are a certain type of DocTypes that are “Single”, i.e. they have no table associated and have only one record of its fields. DocTypes such as Global Defaults, Production Planning Tool are “Single” DocTypes.

#### Field Columns

In the fields table, there are many columns, here is an explanation of the columns of the field table.

<table class="table table-bordered text-left">
	<thead>
		<tr class="active">
			<td width="30%">Column</td>
			<td>Description</td>
		</tr>
		</thead>
		<tbody>
			<tr>
				<td>Label</td>
				<td>Field Label (that appears in the form).</td>
			</tr>
			<tr>
				<td>Type</td>
				<td>Field Type</td>
			</tr>
			<tr>
				<td>Name</td>
				<td>Column name in the database, must be code friendly with no white spaces, special characters and capital letters.</td>
		</tr>
			<tr>
			<td>options</td>
			<td>Field settings:<br>
				For Select: List of options (each on a new line).<br>
				For Link: DocType that is “linked”.<br>
				For HTML: HTML Content
		</tr>
		<tr>
			<td>Perm Level</td>
			<td>Permission level (number) of the field. You can group fields by numbers, called levels, and apply rules on the levels.</td>
		</tr>
		<tr>
			<td>Width</td>
			<td>Width of the field (in pixels) - useful for “Table” types.</td>
		</tr>
		<tr>
			<td>Reqd</td>
			<td>Checked if field is mandatory (required).</td>
		</tr>
		<tr>
			<td>In Filter</td>
			<td>Checked if field appears as a standard filter in old style reports.</td>
		</tr>
		<tr>
			<td>Hidden</td>
			<td>Checked if field is hidden.</td>
		</tr>
		<tr>
			<td>Print Hide</td>
			<td>Checked if field is hidden in Print Formats.</td>
		</tr>
		<tr>
			<td>Report Hide</td>
			<td>Checked if field is hidden in old style reports.</td>
		</tr>
		<tr>
			<td>Allow on Submit</td>
			<td>Checked if this field can be edited after the document is “Submitted”.</td>
		</tr>
		<tr>
			<td>Depends On</td>
			<td>The fieldname of the field that will decide whether this field will be shown or hidden. It is useful to hide un-necessary fields.</td>
		</tr>
		<tr>
			<td>Description</td>
			<td>Description of the field</td>
		</tr>
		<tr>
			<td>Default</td>
			<td>Default value when a new record is created.<br>
			Note: “user” will set the current user as default and “today” will set today’s date (if the field is a Date field).</td>
		</tr>
	<tbody>
<table>

#### Field Types and Options

Here is a list of the different types of fields used to make / customize forms in ERPNext.

<table class="table table-bordered text-left">
	<thead>
		<tr class="active">
			<td width="30%">Type</td>
			<td>Description</td>
			<td>Options/Setting</td>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Data</td>
			<td>Single line text field with 180 characters</td>
			<td>  </td>
		</tr>
		<tr>
			<td>Select</td>
			<td>Select from a pre-determined items in a drop-down.</td>
			<td>The “Options” contains the drop-down items, each on a new row</td>
		</tr>
		<tr>
			<td>Link</td>
			<td>Link an existing document / record</td>
			<td>Options contains the name of the type of document (DocType)</td>
		</tr>
		<tr>
			<td>Currency</td>
			<td>Number with 2 decimal places, that will be shown separated by commas for thousands etc. in Print.</td>
			<td>e.g. 1,000,000.00</td>
		</tr>
		<tr>
			<td>Float</td>
			<td>Number with 6 decimal places.</td>
			<td>e.g. 3.141593</td>
		</tr>
		<tr>
			<td>Int</td>
			<td>Integer (no decimals)</td>
			<td>e.g. 100</td>
		</tr>
		<tr>
			<td>Date</td>
			<td>Date</td>
			<td>Format can be selected in Global Defaults</td>
		</tr>
		<tr>
			<td>Time</td>
			<td>Time</td>
			<td></td>
		</tr>
		<tr>
			<td colspan="3" class="active">Text</td>
		</tr>
		<tr>
			<td>Text</td>
			<td>Multi-line text box without formatting features</td>
			<td></td>
		</tr>
		<tr>
			<td>Text editor</td>
			<td>Multi-line text box with formatting toolbar etc</td>
			<td></td>
		</tr>
		<tr>
			<td>Code</td>
			<td>Code Editor</td>
			<td>Options can include the type of language for syntax formatting.
				Eg JS / Python / HTML</td>
		</tr>
		<tr>
			<td colspan="3" class="active">Table (Grid)</td>
		</tr>
		<tr> 
			<td>Table</td>
			<td>Table of child items linked to the record.</td>
			<td>Options contains the name of the DocType of the child table. For example “Sales Invoice Item” for “Sales Invoice”</td>
		</tr>
		<tr>
			<td colspan="3" class="active">Layout</td>
		</tr>
		<tr>
			<td>Section Break</td>
			<td>Break into a new horizontal section.</td>
			<td>The layout in ERPNext is evaluated from top to bottom.</td>
		</tr>
		<tr>
			<td>Column Break</td>
			<td>Break into a new vertical column.</td>
			<td></td>
		</tr>
		<tr>
			<td>HTML</td>
			<td>Add a static text / help / link etc in HTML</td>
			<td>Options contains the HTML.</td>
		</tr>
		<tr>
			<td colspan="3" class="active">Action</td>
		</tr>
		<tr>
			<td>Button</td>
			<td>Button</td>
			<td>[for developers only]</td>
		</tr>
		<tbody>
	<table>






		