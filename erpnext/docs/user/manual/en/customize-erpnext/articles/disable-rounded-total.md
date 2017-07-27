#Disable Rounded Total

All the sales transactions like Sales Order, Sales Invoice has Rounded Total in it. It calculated based on the value of Grand Total. Also Rounded Total is also visible in the Standard Print Formats. 

<img alt="Print Preview" class="screenshot" src="{{docs_base_url}}/assets/img/articles/hide-rounded-total-1.png">

Follow steps given below to hide rounded total from Standard Print Formats, for all the sales transactions.

#### Step 1: Global Settings

`Setup > Settings > Global Settings`

#### Step 2: Disable Rounded Total

Check Disable Rounded Total, and Save Global Defaults.

<img alt="Print Preview" class="screenshot" src="{{docs_base_url}}/assets/img/articles/hide-rounded-total-2.png">

For system to take effect of this setting, you should clear cache and refresh your ERPNext account. Then your print formats shall not render value for the Rounded Total in the print formats.
   
<div class=well>Note: This setting will only affect Standard print formats.</div>

<!-- markdown -->