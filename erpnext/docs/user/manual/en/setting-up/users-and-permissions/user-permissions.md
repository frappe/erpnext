# User Permissions

Role Base Permissions define the periphery of document types within which a user with a set of Roles can move around in. However, you can have an even finer control by defining User Permissions for a User. By setting specific documents in User Permissions list, you can limit access for that User to specific documents of a particular DocType, on the condition that "Apply User Permissions" is checked in Role Permissions Manager.

To start with, go to:

> Setup > Permissions > User Permissions Manager

User Permissions Manager displaying how users can access only a specific Company.

#### Example

User 'tom.hagen@riosolutions.com' has Sales User role and we want to limit the user to access records for only a specific Company 'Rio Solutions'.

  1. We add a User Permissions row for Company.
	
	<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-new.gif" class="screen" alt="User Permissions For Company">

	Add User Permissions row for a combination of User 'tom.hagen@riosolutions.com' and Company 'Rio Solutions'.

  1. Also Role "All" has only Read permission for Company, with 'Apply User Permissions' checked.
	
	<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-company-role-all.png" class="screen" alt="Role Permissions for All on Company">

	Read Permission with Apply User Permissions checked for DocType Company.

  1. The combined effect of the above two rules lead to User 'tom.hagen@riosolutions.com' having only Read access to Company 'Rio Solutions'.
	
	<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permission-company.png" class="screen" alt="Effect of Role and User Permissions on Company">
	
	Access is limited to Company 'Rio Solutions'.

  1. We want this User Permission on Company to get applied on other documents like Quotation, Sales Order, etc.
	 
	 These forms have a **Link Field based on Company**. As a result, User Permissions on Company also get applied on these documents, which leads to User 'tom.hagen@riosolutions' to acces these documents having Company 'Rio Solutions'.

    <img class="screen" alt="Sales User Role Permissions for Quotation" src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-quotation-sales-user.png" >
	 
	 Users with Sales User Role can Read, Write, Create, Submit and Cancel Quotations based on their User Permissions, since 'Apply User Permissions' is checked.

	<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permission-quotation.png" class="screenshot" alt="Quotation List limited to results for Company 'Rio Solutions'">

	Quotation List is limited to results for Company 'Rio Solutions' for User 'tom.hagen@riosolutions.com'.

  1. User Permissions get applied automatically based on Link Fields, just like how it worked for Quotation. But, Lead Form has 4 Link fields: Territory, Company, Lead Owner and Next Contact By. Say, you want Leads to limit access to Users based only on Territory, even though you have defined User Permissions for DocTypes User, Territory and Company. You can do this by setting 'Ignore User Permissions' for Link fields: Company, Lead Owner and Next Contact By.  
    
<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-lead-role-permissions.png" class="screen" alt="Role Permissions on Lead for Sales User Role">

Sales User can Read, Write and Create Leads limited by User Permissions.

<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-ignore-user-permissions.png" class="screenshot" alt="Set Ingore User Permissions from Setup > Customize > Customize Form">	

Check 'Ingore User Permissions' for Company, Lead Owner and Next Contact By fields using Setup > Customize > Customize Form for Lead.

<img src="{{docs_base_url}}/assets/img/users-and-permissions/permissions-lead-list.png" class="screenshot" alt="Lead List is limited to records with Territory 'United States'">	

Due to the effect of the above combination, User 'tom.hagen@riosolutions.com' can only access Leads with Territory 'United States'.

{next}

