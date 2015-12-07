<h1>Reports in ERPNext</h1>

There are three kind of reports in ERPNext.

###1. Query Report

Query Report is written in SQL which pull values from database and fetch in the report. Though SQL queries can be written from front end, like HTML for customer print format, its restricted from hosted users. Because it will allow users with no access to specific report to query data from query report.

Check Purchase Order Item to be Received report in Stock module for example of Query report.

###2. Script Report

Script Reports are written in Python and stored on server side. These are complex reports which involves exception of logic and calculation. Since these reports are written on server side, its not available for hosted users.

Check Financial Analytics report in Accounts module for example of Script Report.

###3. Report Builder

Report Builder is an in-built report customization tool in ERPNext. This allows you to define fields of the form which shall appear as column in the report. Also you can set required filters and do sorting as per your preference.

Each form in ERPNext has Report Builder option in its list view.

![Report Builder Icon]({{docs_base_url}}/assets/img/articles/Selection_046.png)

####Adding Column in Report

Go to Menu and click on Pick Column option to select field which should be added as column in the report. You can also select the field from the child table (eg. Item table in Sales Invoice) of the form.

![Report Pick Column]({{docs_base_url}}/assets/img/articles/Selection_050.png)

####Applying Filters

All the fields of the form will be applicable for setting filter as well.

![Report Pick Column]({{docs_base_url}}/assets/img/articles/$SGrab_238.png)

####Sorting

Select field based on which report will be sorted.

![Report Pick Column]({{docs_base_url}}/assets/img/articles/Selection_052f7b160.png)

####Save Report

Go to Menu and click on Save button to have this report saved with selected column, filters and sorting.

![Report Pick Column]({{docs_base_url}}/assets/img/articles/$SGrab_241.png)

Saved reports appear under Customize section in the module's home page. Customize Report section only appear if you have custom reports being saved for documents of that module.

![Report Pick Column]({{docs_base_url}}/assets/img/articles/$SGrab_242.png)

<!-- markdown --> 