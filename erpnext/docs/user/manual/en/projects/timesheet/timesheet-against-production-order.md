# Timesheet Against Production Order

#Timesheet based on Production Order

Creating Timesheet for Production Order helps in capacity planning for the Workstations. Also it helps in tracking actual time consumed the Workstation for completing specific operation.

When a Production Order is submitted, based on the Planned Start Date and the availability of the Workstations, system schedules all operations by creating Timesheet.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-capacity-planning.png">

Let's assume we are manufacturing a mobile phone. As per the Bill of Material, time required for the assembly of components could be one hour. However the actual time taken for it's completion could be more than planned. The actual time tracking provides actual operation cost, hence helps in determining accurate valuation of the manufacturing item.

####Production Order

As per the Bill of Materials of manufacturing item, following are the Operations and Workstation through which raw-material items are processed.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-production-order-1.png">

On submission on Production Order, Timesheet will be created automatically.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-production-order-2.png">

####Time Sheet created from Production Order

In the Timesheet, unique row will be added for each Operation - Workstation. This allows operator/supervisor at the workstation to enter actual From Time and To Time taken for each Operation.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-production-order-3.gif">

After enter From Time and To Time for all the Operations, Total Hours will be calculated.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-production-order-6.png">

With updating actual time, you can also enter "Completed Qty". If all the items are not processed in the same Timesheet, you can create another Timesheet from the Production Order.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-production-order-4.png">

####Save and Submit Timesheet

On the submission of Timesheet, Total Hours is calculated. Also, in the Production Order, for each Operation, actual Start and End Time is updated.

<img class="screenshot" alt="Sales Invoice" src="{{docs_base_url}}/assets/img/project/timesheet/timesheet-production-order-5.png">
