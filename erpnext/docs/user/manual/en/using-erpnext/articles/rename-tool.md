<h1>Rename Tool</h1>

ERPNext has Renaming Tool which allows you to rectify/change record id for existing records. This facility can be only performed by User with System Manager's role.

There are two ways you can rename records in your account. You can follow the approach based on how many records needs to be renamed.

###Rename Record via Rename Tool

Using this tool you can correct/rectify primary ids of 500 records at a time.

Following are step to rename bulk records in ERPNext. Let's assume we are renaming Item Codes for existing Items.

#### Step 1: Open Excel File

In new excel file enter old Item Ids in one column and enter new Item Ids in exact next column. Then save data file in .csv format.

![Data File]({{docs_base_url}}/assets/img/articles/Selection_018ef32b6.png)

#### Step 2: Upload Data File

To upload data file go to,

`Setup > Data > Rename Tool`

Select DocType which you want to rename. Here DocType will be Item. Then Browse and Upload data file.

![Upload Data]({{docs_base_url}}/assets/img/articles/Selection_0173436a8.png) 

Following are the renamed Item Codes.

![New Name]({{docs_base_url}}/assets/img/articles/Selection_019bf0547.png)

###Rename Individual Document

Click [here](https://erpnext.com/kb/tools/renaming-documents) for detailed steps on how to rename document one by one.

<!-- markdown -->