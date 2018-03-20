#Setting Up Dropbox Backups

We always recommend customers to maintain backup of their data in ERPNext. The database backup is downloaded in the form of an SQL file. If needed, this SQL file of backup can be restored in the another ERPNext account as well.

You can automate database backup download of your ERPNext account into your Dropbox account.

To setup Dropbox Backup,
`Explore > Integrations > Dropbox Settings`

##Steps are different for ERPnext managed versions and open-source versions

###ERPnext Managed Version Instructions

####Step 1: Set Frequency

Set Frequency to download backup in your Dropbox account.

<img class="screenshot" alt="set frequency" src="{{docs_base_url}}/assets/img/setup/integrations/setup-backup-frequency.png">

####Step 2: Allow Dropbox Access

After setting frequency and updating other details, click on `Allow Dropbox access`. On clicking this button, the Dropbox login page will open in the new tab. This might require you to allow pop-up for your ERPNext account.

####Step 3: Login to Dropbox

Login to your Dropbox account by entering login credentials.

<img class="screenshot" alt="Login" src="{{docs_base_url}}/assets/img/setup/integrations/dropbox-2.png">

####Step 4: Allow

On successful login, you will find a confirmation message as following. Click on "Allow" to let your ERPNext account have access to your Dropbox account.

<img class="screenshot" alt="Allow" src="{{docs_base_url}}/assets/img/setup/integrations/dropbox-3.png">

With this, a folder called "ERPNext" will be created in your Dropbox account, and database backup will start to auto-download in it.


##Open Source Version Instructions

####Step 1: Login to Dropbox Developer area

<a href="https://www.dropbox.com/developers/apps" target="_blank" style="line-height: 1.42857143;">https://www.dropbox.com/developers/apps</a>

####Step 2: Create a new Dropbox app

<img class="screenshot" alt="Create new" src="{{docs_base_url}}/assets/img/setup/integrations/dropbox-open-3.png">

####Step 3: Fill in the details for your new app

<img class="screenshot" alt="Choose Dropbox API and type as APP Folder" src="{{docs_base_url}}/assets/img/setup/integrations/dropbox-open-1.png">

-
<img class="screenshot" alt="Setup APP Name" src="{{docs_base_url}}/assets/img/setup/integrations/dropbox-open-2.png">

####Step 4: Insert your custom domain Redirect URI

`https://{yourwebsite.com}/api/method/frappe.integrations.doctype.dropbox_settings.dropbox_settings.dropbox_auth_finish`

<img class="screenshot" alt="Set Redirect URL" src="{{docs_base_url}}/assets/img/setup/integrations/dropbox_redirect_uri.png">

####Step 5: In a new window, open the Dropbox Settings page in your ERPnext installation

####Step 6: Set backup frequency and email

Set the frequency to download your site backups to your Dropbox account.

<img class="screenshot" alt="set frequency" src="/docs/assets/img/setup/integrations/setup-backup-frequency.png">

####Step 7: Input Keys from your Dropbox App window

From your Dropbox App page, enter the app key and (unhidden) app secret into the ERPnext Dropbox settings page.

Alternatively, you can enter it manually in `sites/{sitename}/site_config.json` as follows,

<div>
	<pre>
		<code>{ 
 "db_name": "demo", 
 "db_password": "DZ1Idd55xJ9qvkHvUH", 
 "dropbox_access_key": "ACCESSKEY", 
 "dropbox_secret_key": "SECRECTKEY" 
} 		
		</code>
	</pre>
</div>

####Step 8: Click Save before continuing!!!

####Step 9: After saving, click "Allow Dropbox Access"

The Dropbox login page will open in the new tab. This might require you to allow pop-up for your ERPNext account.

####Step 11: Allow Dropbox Access

On successful login, you will find a confirmation message as following. Click on "Allow" to let your ERPNext account have access to your Dropbox account.

<img class="screenshot" alt="Allow" src="/docs/assets/img/setup/integrations/dropbox-3.png">

####Step 12: Confirm Backups Work

From the ERPnext Dropbox page, click `Take Backup Now` and then go to you Dropbox files view. You should see a new folder in Dropbox named `Apps` and inside of it your {New App} folder. Inside of it should be backup folders for both files and database.
