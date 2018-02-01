# Retain Sample Stock

A sample of a batch of starting material, packaging material or finished product is stored for the purpose of being analyzed should the need arise later.

### Set Sample Retention Warehouse in Stock Settings

It is advised to create a new warehouse just for retaining samples and not use it in production.

<img class="screenshot" alt="Sample Retention Warehouse" src="/docs/assets/img/stock/sample-warehouse.png">

### Enable Retain Sample in Item master

Check Retain Sample and Maximum allowed samples in Item Master for a batch. Please note that Retain Sample is based
on Batch hence Has Batch No should be enabled as well.

<img class="screenshot" alt="Retain Sample" src="/docs/assets/img/stock/retain-sample.png">

### Stock Entry

Whenever a Stock Entry is created with the purpose as Material Receipt, for items which have Retain Sample enabled, the Sample Quantity can be set during that Stock Entry. Sample quantity cannot be more than the Maximum sample quantity set in Item Master.

<img class="screenshot" alt="Retain Sample" src="/docs/assets/img/stock/material-receipt-sample.png">

On submission of this Stock Entry, button 'Make Retention Stock Entry' will be available to make another Stock Entry for the transfer of sample items from the mentioned batch to the retention warehouse set in Stock Settings. On clicking this button it will direct you to new Stock Entry with all the information, verify the information and click Submit.

<img class="screenshot" alt="Retain Sample" src="/docs/assets/img/stock/material-transfer-sample.png">