The Data Import Tool is a great way to upload (or edit) bulk data, specially master data, into the system.

To Open the data import tool, you either go to Setup or go to the Transaction you want to Import. If Data Import is allowed, you will see an Import Button:

<img alt="Start Import" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/data-import-1.png">

The tool has two sections, one to download a template and the second to upload
the data.

(Note: Only those DocTypes are allowed for Import whose Document Type is
"Master" or Allow Import property is set.)

### 1\. Downloading The Template

Data in ERPNext is stored in tables, much like a spreadsheet with columns and
rows of data. Each entity in ERPNext can have multiple child tables associated
with it too. The child tables are linked to the parent tables and are
implemented where there are multiple values for any property. For example an
Item can have multiple prices, An Invoice has multiple Items and so on.

  * Select Doctype for which template should be downloaded.
  * Check fields to be included in the template.
  * Click on "Download Blank Template".
  * For bulk editing, you can click on "Download With Data".
  
<img alt="Download Template" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/data-import-tool-template.gif">

### 2\. Fill in the Template

After downloading the template, open it in a spreadsheet application and fill
in the data below the column headings.

<img alt="Download Template" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/import-file.png">

Then export your template or save it as a Excel or Comma Separated Values (CSV)
file. To export the document in Excel tick the checkbox for Download in Excel File Format 

<img alt="Download Template" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/import-csv.png">

### Download in Excel

<img alt="Download Template" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/data-import-excel.png">

### 3\. Upload the File ethier in .xlsx or .csv 

Finally attach the  file in the section. Click on the "Upload". Once the upload is successfull click Import"
button.

<img alt="Upload" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/data-import-3.png">


<img alt="Upload" class="screenshot" src="{{docs_base_url}}/assets/img/setup/data-import/data-import-4.png">

#### Notes:

1. Make sure that if your application allows, use encoding as UTF-8.
1. Keep the ID column blank for new records.

### 4. Uploading All Tables (Main + Child)

If you select all tables, you will get columns belonging to all the tables in
one row separated by `~` columns.

If you have multiple child rows then you must start a new main item on a new
row. See the example:


    Main Table                          ~   Child Table
    Column 1    Column 2    Column 3    ~   Column 1    Column 2    Column 3
    v11         v12         v13             c11         c12         c13
                                            c14         c15         c17
    v21         v22         v23             c21         c22         c23

> To see how its done, enter a few records manually using forms and export
"All Tables" with "Download with Data"

### 5. Overwriting

ERPNext also allows you to overwrite all / certain columns. If you want to
update certain columns, you can download the template with data. Remember to
check on the “Overwrite” box before uploading.

> Note: For child records, if you select Overwrite, it will delete all the
child records of that parent.

### 6. Upload Limitations

ERPNext restricts the amount of data you can upload in one file. Though the
number may vary based on the type of data. It is usually safe to upload around
1000 rows of a table at one go. If the system will not accept, then you will
see an error.

Why is this? Uploading a lot of data can cause your system to crash, specially
if there are other users doing things in parallel. Hence ERPNext restricts the
number of “writes” you can process in one request.

***

#### How to Attach files?

When you open a form, on the right sidebar, you will see a section to attach
files. Click on “Add” and select the file you want to attach. Click on
“Upload” and you are set.

#### What is a CSV file?

A CSV (Comma Separated Value) file is a data file that you can upload into
ERPNext to update various data. Any spreadsheet file from popular spreadsheet
applications like MS Excel or Open Office Spreadsheet can be saved as a CSV
file.

If you are using Microsoft Excel and using non-English characters, make sure
to save your file encoded as UTF-8. For older versions of Excel, there is no
clear way of saving as UTF-8. So save your file as a CSV, then open it in
Notepad, and save as “UTF-8”. (Sorry blame Microsoft for this!)

####Help Video on Importing Data in ERPNext from Spreadsheet file



<iframe width="660" height="371" src="https://www.youtube.com/embed/Ta2Xx3QoK3E" frameborder="0" allowfullscreen></iframe>

{next}
