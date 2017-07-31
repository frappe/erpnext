# Sales Person Target Allocation

With management of Sales Person, ERPNext also allow you to assign target to Sales Persons based on Item Group and Territory. Based on target allocated and actual sales booked by Sales Person, you will get target variance report for the Sales Person.

###1. Sales Person - Item Groupwise Target Allocation

####1.1 Open Sales Person's Master

To allocate target, you should open specific Sales Person master.

`Selling > Setup > Sales Person > (Open Sales Person)`

####1.2 Allocate Item Groupwise Target

In the Sales Person master, you will find table called Sales Person Target.

<img class="screenshot" alt="Sales person target " src="{{docs_base_url}}/assets/img/selling/sales-person-target-item-group.png">

In this table, you should select Item Group, Fiscal Year, Target Qty and Amount. 

<div class=well>You can give target in amount or quantity, or in both. Item Group can also be left blank. In this case the system will calculate target based on all the Items.</div>

####1.3 Target Distribution

If you wish to spread allocated target across months, then you should setup Monthly Distribution master, and select it in the Sales Person master. Considering our example, target for the month of December will be set as 5 qty (10% of total allocation).


<img class="screenshot" alt="Target Distribution" src="{{docs_base_url}}/assets/im/selling/sales-person-target-distribution.gif">

####Report - Sales Person Target Variance Item Groupwise

To check this report, go to:

`Selling > Standard Report > Sales Person Target Variance (Item Group-wise)'

This report will provide you variance between target and actual performance of Sales Person. This report is based on Sales Order report.


<img class="screenshot" alt="Target Item Group" src="{{docs_base_url}}/assets/img/selling/sales-person-item-group-report.png">

As per the report, allocated target to Sales Person for the month of December was 5 qty. However, Sales Order was made for this employee and Item Group for only 3 qty. Hence, variance of 2 qty is shown in the report.

---

###2. Sales Person - Territorywise Target Allocation

To allocate target to Sales Person based on Territory, you can should select specific Sales Person in the Territory master. This Sales Person is entered just for the reference. Sales Person details are not updated in the variance report of Territorywise Target Allocation.

####2.1 Go to Territory master

`Selling > Setup > Territory > (Open specific Territory master)`

In the Territory master, you will find field to select Territory Manager. This field is linked to "Sales Person" master.

<img class="screenshot" alt="Sales Person Territory Manager" src="{{docs_base_url}}/assets/img/selling/sales-person-territory-manager.png">

####2.2 Allocating Target

Target Allocation in the Territory master is same as in Sales Person master. You can follow same steps as given above to specify target in the Territory master as well.

####2.3 Target Distribution

Using this Monthly Distribution document, you can divide target Qty or Amount across various months.

####2.4 Report - Territory Target Variance Item Groupwise

This report will provide you variance between target and actual performance of Sales in particular territory. This report is based on Sales Order report. Though Sales Person is defined in the Territory master, its details are not pulled in the report.

<img class="screenshot" alt="Sales Person Territory Report" src="{{docs_base_url}}/assets/img/selling/sales-person-territory-report.png">

---

###3. Target Distribution

Target Distribution document allows you to divide allocated target across multiple months. If your product and services is seasonal, you can distribute the sales target accordingly. For example, if you are into umbrella business, then target allocated in the monsoon seasion will be higher than in other months.

To create new Monthly Distriibution, go to:

`Accounts > Monthly Distributon`

<img class="screenshot" alt="Target Distribution" src="{{docs_base_url}}/assets/img.selling/erpnext/target-distribution.png">

You can link Monthly Distribution while allocating targets in Sales Person as well as in Territory master.

###See Also

1. [Sales Person Target Allocation]({{docs_base_url}}/user/manual/en/selling/setup/sales-person-target-allocation)
2. [Using Sales Person in transactions]({{docs_base_url}}/user/manual/en/selling/articles/sales-persons-in-the-sales-transactions)

{next}
