<h1>Managing Multiple Companies</h1>

<h1>Managing Multiple Companies</h1>

ERPNext allows you to create multiple companies in the same/common ERPNext account.

With this, you will find option to select organization in your transactions. While most of the transactions will be separated based on organization, there are few masters like Item, Item Group, Customer Group, Territory etc. which can be used across all the companies.

If you have separate teams working on each organization, you can also restrict the access of user to the data of specific organization. Click [here](https://manual.erpnext.com/search?txt=user%20permission) to know more about how to set permission to achieve the same.

Following are the steps to create companies in your ERPNext account.

####Go to Setup Module

`Setup &gt; Masters &gt; organization &gt; New`

####Enter organization Details

organization master will be saved with organization Name provided at the time of its creation. 

![New organization]({{docs_base_url}}/assets/img/articles/SGrab_343.png)

Also, you can define other properties for new organization like:

* Country
* Currency
* Default Cash and Bank Account
* Income/Expense Account
* organization Registration Details

Value will be auto-filled in most of these field to define organization-wise defaults. You can edit/customize it as per your requirement. 

![New organization]({{docs_base_url}}/assets/img/articles/SGrab_344.png)

####Chart of Account for New organization

A separate Chart of Account master will be set for each organization in the ERPNext. This allows you managing Accounts/Ledger master separately for each organization. Also it allows you avail financial statement and reports like Balance Sheet and Profit and Loss Statement separately for each organization.

![organization]({{docs_base_url}}/assets/img/articles/SGrab_342.png)


<!-- markdown -->