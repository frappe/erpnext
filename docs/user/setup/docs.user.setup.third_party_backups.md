---
{
	"_label": "Third Party Backups"
}
---

If you wish to store your backups on a periodic basis,on Dropbox, you can do it directly through ERPNext.

> Setup > Manage 3rd Party Backups



![Third Party Backups](img/third-party-backups.png)


On the Backup Manager page, enter the email addresses of those people whom you wish to notify about the upload status. Under the topic 'Sync with Dropbox', select whether you wish to upload Daily, Weekly or Never. The third step is to click on **Allow Dropbox Access**.

> Tip: In future, if you wish to discontinue uploading backups to dropbox, then select the Never option.

![Backup Manager](img/backup-manager.png)



 You need to login to your dropbox account, with your user id and password.



![Dropbox Access](img/dropbox-access.png)



## Open Source Users


Installing Pre-Requisites

    pip install dropbox
    pip install google-api-python-client

<br>
#### Create an App in Dropbox

First create your Dropbox account.After successful creation of account you will receive `app_key`, `app_secret` and `access_type`. Now open `conf.py` and set `app_key` as `dropbox_access_key` and `app_secret` as `dropbox_secret_key` 


<br>
> Note: Please ensure Allow Pop-ups are enabled in your browser.
