#Reports in ERPNext

There are three kind of reports in ERPNext.

###1. Report Builder

Report Builder is an in-built report customization tool in ERPNext. This allows you to define specific fields of the form which shall be added in the report. Also you can set required filters, sorting and give preferred name to report.

<iframe width="660" height="371" src="https://www.youtube.com/embed/y0o5iYZOioU" frameborder="0" allowfullscreen></iframe>

### 2. Query Report

Query Report is written in SQL which pull values from account's database and fetch in the report. Though SQL queries can be written from front end, like HTML, its restricted in hosted users. Because it will allow users with no access to specific report to query data directly from the database.

Check Purchase Order Item to be Received report in Stock module for example of Query report. Click [here](https://frappe.github.io/frappe/user/en/guides/reports-and-printing/how-to-make-query-report.html) to learn how to create Query Report.

### 3. Script Report

Script Reports are written in Python and stored on server side. These are complex reports which involves logic and calculation. Since these reports are written on server side, customizing it from hosted account is not possible. 

Check Financial Analytics report in Accounts module for example of Script Report. Click [here](https://frappe.github.io/frappe/user/en/guides/reports-and-printing/how-to-make-script-reports.html) to learn how to create Script Report.

<!-- markdown --> 