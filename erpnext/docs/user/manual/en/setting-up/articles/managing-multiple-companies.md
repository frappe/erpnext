#Managing Multiple Companies

ERPNext allows you to create multiple companies in a single ERPNext instance.

In one account has multiple companies, you will find option to select Company in each transactions. While most of the records (mostly transactions) will be separated based on Company, there are few masters like Item, Item Group, Customer Group, Territory etc. which are common among all the companies.

If you have separate teams working on each company, you can restrict access of the User to the data of specific Company. Click [here](/docs/user/manual/en/setting-up/users-and-permissions/) to know how to set permission rules for giving restricted access to the User.

Following are the steps to add new Company.

####Go to Setup Module

`Accounts > Setup > Company > New`

####Enter Company Details

Company will be saved with Company Name provided.

<img alt="New Company" class="screenshot" src="/docs/assets/img/articles/new-company-1.png">

Also, you can define other properties for new company like:

* Country
* Currency
* Default Cash and Bank Account
* Income/Expense Account
* Company Registration Details

Value will be auto-filled in most of these field to define company-wise defaults. You can edit/customize it as per your requirement. 

<img alt="New Company" class="screenshot" src="/docs/assets/img/articles/new-company-2.png">

####Chart of Account for New Company

A separate Chart of Account master will be set for each company in the ERPNext. This allows you managing Accounts/Ledger master separately for each company. Also it allows you avail financial statement and reports like Balance Sheet and Profit and Loss Statement separately for each company.

<img alt="New Company" class="screenshot" src="/docs/assets/img/articles/new-company-3.png">

<!-- markdown -->