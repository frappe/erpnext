<h1>Fixing Fiscal Year's Error</h1>

While creating entries in ERPNext, system validates if dates (like Posting Date, Transaction Date etc.) matches with Fiscal Year selected in the entry. If not, system through an error message saying:

`Date ##-##-#### not in fiscal year`

You are more likely to receive this error message if your Fiscal Year has changes, but you still have old Fiscal Year updated. To ensure new Fiscal Year is auto updated in the transactions, you should setup your master as instructed below.

####Create New Fiscal Year

Only User with System Manager's Role Assigned has permission to create new Fiscal Year. To create new Fiscal Year, go to:

`Accounts > Setup > Fiscal Year`

Click [here](https://erpnext.com/user-guide/accounts/fiscal-year) to learn more about Fiscal Year master.

####Set Fiscal Year as Default

After Fiscal Year is saved, you will find option to set that Fiscal year as Default.

![Fiscal Year Default]({{docs_base_url}}/assets/img/articles/$SGrab_393.png)

Default Fiscal Year will be updated in the Global Default setting as well. You can manually update Default Fiscal Year from:

`Setup > Settings > Global Default`

![Fiscal Year Global Default]({{docs_base_url}}/assets/img/articles/$SGrab_394.png)

Then Save Global Default, and refresh browser of your ERPNext account. After this, you will have default Fiscal Year auto-updated in your transactions as well.

Note: In transactions, you can manually select required Fiscal Year from More Info section. You might have to click on "View Details" button to access View Details section, and edit Fiscal Year.
<!-- markdown -->