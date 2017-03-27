# Role Permission for Page and Report

In ERPNext, user can make his custom UI using page and the custom report using report builder or query report. ERPNext has role based permission system where user can assign roles to the user and sames roles can assign to the page and report to access them. 

If user has enbaled the developer mode then, they can add the roles in the table of page and report. With this user can transfer the roles of page and report to the production server from the develop server.

### For Page
<img alt="Assign roles to the page" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/roles-for-page.png">

### For Report
<img alt="Assign roles to the report" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/roles-for-report.png">

## Tool for custom roles assignment

If developer mode is disabled then user can assign the roles to the page, report using tool Role Permission for Page and Report. The changes can be apply only for the respective database, it not make changes in the code base. 

To access, goto Setup > Permissions > Role Permission for Page and Report

<img alt="Tools to assign custom roles to the page" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/role-permission-for-page-and-report.png">

### Reset to defaults

Using reset to defaults button, user can remove the custom roles applied on the page or report and set the roles which has been alredy available on the respective page or report.

<img alt="Reset the default roles" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/reset-roles-permisison-for-page-report.png">
