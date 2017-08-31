# Capacity Planning based on Production Order

Capacity Planning functionality helps you in tracking production jobs allocated on each Workstation.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/capacity-1.png">

Follow are the steps to use Capacity Planning Feature in your ERPNext account.

1.  Operations  

    To add operations, go to:  

    `Manufacturing > Bill of Materials > Operations`

2.  Workstation  

    Add each Workstation in your ERPNext account from:  

    `Manufacturing > Bill of Materials > Workstation` 

    In the Workstation master, you can define which operations will be performed on it, what are the cost associated with it, and what are the working hours of that Workstation.  

3.  Bill of Materials (BOM):  

    In a BOM, with the list of raw material needed, for manufacturing, you can also list operation and workstations through which those raw materials will be processed.  

4.  Production Order:  

    On submission of Production Order, Timesheet for Operations. This helps you allocate production jobs on each Workstation, as well as you can update actual time taken for each Operation.  

### Error due to Capacity Planning

**Question:** On Submission of Production Order, we are getting following error message.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/capacity-2.png">

**Answer: **Please check if you have updated Working Hours in the Workstation master? If not, then please update it and then try to submit Production Order.

On submission of Production Order, Operations (as added in the BOM) are allocated on the workstation. Each operation should start and end on the same day. If a system is not able to schedule that operation in a day, then system request you to divide that Project, so that system can allocate smaller operations in a day.

If you have update working hours in the Workstation, but still getting this issue, that because one of your operation is taking too long, and cannot be completed in a day. Please divide that operation into smaller operations, so that it can be allocated on Workstation and completed on the same day.

### Avoid Working Hours of Workstation

If you want to ignore above validation and allow scheduling of production job beyond the working hours of the Workstation, enable
Overtime in the Manufacturing Settings.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/capacity-3.png">

If you want to complete disable Capacity Planning feature, in the Manufacturing Settings, check field "Disable Capacity Planning and Time Tracking".

