# Role Permission for Page and Report

In ERPNext, user can make his custom user interface using Page and the custom report using Report Builder or Query Report. ERPNext has role-based-permission system where user can assign roles to the user. And the same role can be assigned to the page and report, to access them.

If user has enabled the developer mode, then they can add the roles directly in the page and report record. But in that case, the permissions will also be reflected in the json file for the page / report.

### For Page
<img alt="Assign roles to the page" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/roles-for-page.png">

### For Report
<img alt="Assign roles to the report" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/roles-for-report.png">

## Tool for custom roles assignment

If developer mode is disabled, then user can assign the roles to the page and report, using "Role Permission for Page and Report" page.

To access, goto Setup > Permissions > Role Permission for Page and Report

<img alt="Tools to assign custom roles to the page" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/role-permission-for-page-and-report.png">

### Reset to defaults

Using "Reset to Default" button, user can remove the custom permissions applied on a page or report. Then default permissions will be applicable on that page or report.

<img alt="Reset the default roles" class="screenshot" src="{{docs_base_url}}/assets/img/users-and-permissions/reset-roles-permisison-for-page-report.png">
