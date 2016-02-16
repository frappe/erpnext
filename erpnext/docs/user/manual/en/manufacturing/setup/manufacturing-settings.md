#Manufacturing Settings

Manufacturing Settings can be found at:

`Manufacturing > Setup > Manufacturing Settings`

<img class="screenshot" alt="Manufacturing Settings" src="{{docs_base_url}}/assets/img/manufacturing/manufacturing-settings-1.png">

####Disable Capacity Planning and Time Tracking

As per Capacity Planning feature, when Production Order is created for an item, for each Operation, Time Log is created. Based on actual Operation Time, Time Logs is updated. This also provides total Operations Cost against Production Order.

If you don't track actual operations time, and want to disable creation of Time Log based on Operations, you should check "Disable Capacity Planning and Time Tracking" in the Manufacturing Settings.

####Allow Overtime

In the Workstation master, actual working hours are defined (say 101m to 6pm). As per the Capacity Planning, Time Logs are created against Workstation, for tracking actual operations hour. It also considers working hours of a Workstation when scheduling job (via Time Log). 

<img class="screenshot" alt="Manufacturing Settings" src="{{docs_base_url}}/assets/img/articles/manufacturing-settings-2.png">

As per the standard validation, if Operation cannot be completed within working hours of Workstation, then user is asked to divide an Operation into multiple and smaller Operations. However, if `Allow Overtime` field is checked, while creating Time Logs for Operation, working hours of Workstation will not be validated. In this case, Time Logs for Operation will be created beyond working hours of Workstation as well.

####Allow Production on Holidays

Holiday of a company can be recorded in the [Holiday List]({{docs_base_url}}/user/manual/en/human-resources/) master. While scheduling production job on workstation, system doesn't consider a day listed in the Holiday list. If you want production job to be scheduled on holidays as well, `Allow Production on Holidays` field should be checked.

<img class="screenshot" alt="Manufacturing Settings" src="{{docs_base_url}}/assets/img/articles/manufacturing-settings-3.png">

####Over Production Allowance Percentage

In Production Order, `Qty to Manufacture` is set. When creating Manufacture entry against Production Order, it validates `Qty to Manufature` entered in production order, and doesn't allow creating Manufacture Entry for more qty and Production Order qty. If you want to create Manufacture Qty than Production Order qty, mention Over Production Allowance Qty in the Manufacturing Settings. Based on Allowance Percentage mentioned, you will be able to create Manufacture Entry for more Qty than in Production Order.

####Back-flush Raw Materials Based On

When creating Manufacture Entry, raw-material items are back-flush based on BOM of production item. If you want raw-material items to be back-flushed based on Material Transfer entry made against that Production Order instead, then you should set Back-flush Raw Materials Based On "Material Transferred for Manufacture".

<img class="screenshot" alt="Manufacturing Settings" src="{{docs_base_url}}/assets/img/articles/manufacturing-settings-4.png">

####Capacity Planning For (Days)

Define no. of days for which system will do production job allocation in advance.

####Time Between Operations (in mins)

Time gap between two production operations.

####Default Work In Progress Warehouse

This Warehouse will be auto-updated in the Work In Progress Warehouse field of Production Order.

####Default Finished Goods Warehouse

This Warehouse will be auto-updated in the Work In Progress Warehouse field of Production Order.