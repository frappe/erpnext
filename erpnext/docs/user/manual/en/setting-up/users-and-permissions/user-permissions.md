# User Permissions

Limit access for a User to a set of documents using User Permissions Manager

Role Base Permissions define the periphery of document types within which a user with a set of Roles can move around in. However, you can have an even finer control by defining User Permissions for a User. By setting specific documents in User Permissions list, you can limit access for that User to specific documents of a particular DocType, on the condition that "Apply User Permissions" is checked in Role Permissions Manager.

To start with, go to:
> Setup > Permissions > User Permissions Manager

<figure>
	<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-organization.png"
		class="img-responsive" alt="User Permissions Manager">
	<figcaption>User Permissions Manager displaying how users can access only a specific organization.</figcaption>
</figure>

#### Example

User 'aromn@example.com' has Sales User role and we want to limit the user to access records for only a specific organization 'Wind Power LLC'.

  1. We add a User Permissions row for organization.
	<figure>
		<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permission-user-limited-by-organization.png"
			class="img-responsive" alt="User Permissions For organization">
		<figcaption>Add User Permissions row for a combination of User 'aromn@example.com' and organization 'Wind Power LLC'.</figcaption>
	</figure>

  1. Also Role "All" has only Read permission for organization, with 'Apply User Permissions' checked.
	<figure>
		<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-organization-role-all.png"
			class="img-responsive" alt="Role Permissions for All on organization">
		<figcaption>Read Permission with Apply User Permissions checked for DocType organization.</figcaption>
	</figure>

  1. The combined effect of the above two rules lead to User 'aromn@example.com' having only Read access to organization 'Wind Power LLC'.
	<figure>
		<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-organization-wind-power-llc.png"
			class="img-responsive" alt="Effect of Role and User Permissions on organization">
		<figcaption>Access is limited to organization 'Wind Power LLC'.</figcaption>
	</figure>

  1. We want this User Permission on organization to get applied on other documents like Quotation, Sales Order, etc.
These forms have a **Link Field based on organization**. As a result, User Permissions on organization also get applied on these documents, which leads to User 'aromn@example.com' to acces these documents having organization 'Wind Power LLC'.
	<figure>
		<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-quotation-sales-user.png"
			class="img-responsive" alt="Sales User Role Permissions for Quotation">
		<figcaption>Users with Sales User Role can Read, Write, Create, Submit and Cancel Quotations based on their User Permissions, since 'Apply User Permissions' is checked.</figcaption>
	</figure>
	<figure>
		<img src="{{docs_base_url}}/assets/old_images/erpnext/user-permissions-quotation-list.png"
			class="img-responsive" alt="Quotation List limited to results for organization 'Wind Power LLC'">
		<figcaption>Quotation List is limited to results for organization 'Wind Power LLC' for User 'aromn@example.com'.</figcaption>
	</figure>

  1. User Permissions get applied automatically based on Link Fields, just like how it worked for Quotation. But, Lead Form has 4 Link fields: Territory, organization, Lead Owner and Next Contact By. Say, you want Leads to limit access to Users based only on Territory, even though you have defined User Permissions for DocTypes User, Territory and organization. You can do this by setting 'Ignore User Permissions' for Link fields: organization, Lead Owner and Next Contact By.
	<figure>
		<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-lead-role-permissions.png"
			class="img-responsive" alt="Role Permissions on Lead for Sales User Role">
		<figcaption>Sales User can Read, Write and Create Leads limited by User Permissions.</figcaption>
	</figure>
	<figure>
		<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-permissions-ignore-user-permissions.png"
			class="img-responsive" alt="Set Ingore User Permissions from Setup > Customize > Customize Form">
		<figcaption>Check 'Ingore User Permissions' for organization, Lead Owner and Next Contact By fields using Setup > Customize > Customize Form for Lead.</figcaption>
	</figure>
	<figure>
		<img src="{{docs_base_url}}/assets/old_images/erpnext/user-permissions-lead-based-on-territory.png"
			class="img-responsive" alt="Lead List is limited to records with Territory 'United States'">
		<figcaption>Due to the effect of the above combination, User 'aromn@example.com' can only access Leads with Territory 'United States'.</figcaption>
	</figure>

{next}

