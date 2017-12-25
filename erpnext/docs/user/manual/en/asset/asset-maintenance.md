# Asset Maintenance Management
ERPNext provides features to track the details of individual maintenance/calibration tasks for an asset by date, the person responsible for the maintenance and future maintenance due date.

To perform Asset Maintenance in ERPNext,

  1. Enable Asset Maintenance.
  2. Create Asset Maintenance Team.
  3. Create Asset Maintenance.
  4. Create Asset Maintenance Log.
  5. Create Asset Repair Log.

### Enable Asset Maintenance
Check Maintain Required in Asset to enable Asset Maintenance
<img class="screenshot" alt="Asset" src="/docs/assets/img/asset/maintenance_required.png">

### Asset Maintenance Team
Create Asset Maintenance Team, select team members and their role.
<img class="screenshot" alt="Asset" src="/docs/assets/img/asset/asset_maintenance_team.png">


### Asset Maintenance
For each asset create a Asset Maintenance record listing all the associated maintenance tasks, maintenance type (Preventive Maintenance or Calibration), periodicity, assign to and start and end date of maintenance. Based on start date and periodicity the next due date is auto-calculated and a ToDo is created for the Assignee.
<img class="screenshot" alt="Asset" src="/docs/assets/img/asset/asset_maintenance.png">

### Asset Maintenance Log
For each task in Asset Maintenance, Asset Maintenance Log is auto created to keep track of the upcoming Maintenances. It will have status, completion date and actions performed. Based on completion date here, next due date is calculated automatically and new Asset Maintenance Log is created.
<img class="screenshot" alt="Asset" src="/docs/assets/img/asset/asset_maintenance_log.png">

### Asset Repair
You can also maintain the records of Repair/Failures of your asset which are not listed in Asset Maintenance.
<img class="screenshot" alt="Asset" src="/docs/assets/img/asset/asset_repair.png">