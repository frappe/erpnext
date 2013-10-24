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

