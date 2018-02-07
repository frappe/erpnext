# User Permissions

Along with Role based permissions, you can also set user level permissions that are based on rules that are evaluated against the data containted in the document being accessed. This is particularly useful when you want to restrict based on:

1. Allow user to access data belonging to one Company
1. Allow user to access data related to a specific Customer or Territory

### Creating User Permissions

To create a User Permission, go to Setup > Permission > User Permissions

When you create a new record you will have to specify

1. The user for which the rule has to be applied
1. The type of document which will be allowed (for example "Company")
1. The specific item that you want to allow (the name of the "Company)

<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-perms/new-user-permission.png" class="screenshot" alt="Creating a new user permission">

If you want to apply the permissions to all Roles for that user, keep the "Apply Permissions for all Roles of this User" checked. If you check this, it will automatically setup the rules for Roles to check for User Permissions.

### Choosing Which Roles to Apply

You can also manually edit the the roles for which you want the user permissions to apply. To do that go the the **Role Permission Manager** and select the role for which you want to Edit the User Permissions.

Note that the "Apply User Permissions" is already checked for this role. Then click on "Select Document Types"

<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-perms/select-document-types.png" class="screenshot" alt="Select Document Types to Edit the Setting">

Here you will see that Company has already been checked. If you want user permissions not be applied for that particular rule, you can un check it.

<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-perms/view-selected-documents.png" class="screenshot" alt="Select Document Types to Edit the Setting">

### Ignoring User Permissions on Certain Fields

Another way of allowing documents to be seen that have been restricited by User Permissions is to check "Ignore User Permissions" on a particular field by going to **Customize Form**

For example you don't want Assets to be restricited for any user, then select **Asset** in **Customize Form** and in the Company field, check on "Ignore User Permissions"

<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-perms/ignore-user-user-permissions.png" class="screenshot" alt="Ignore User Permissions on specific properties">

### Strict Permisssions

Since User Permissions are applied via Roles, there may be many users belonging to a particular Role. Suppose you have three users belonging to Role "Accounts User" and you have applied **User Permissions** to only one user, then the permissions will only be restricted to that user.

You can change this setting incase you want the user permissions to be assigned to all users, even if they are not assigned any user permissions by going to **System Settings** and checking "Apply Strict User Permissions"

### Checking How User Permissions are Applied

Finally once you have created your air-tight permission model, and you want to check how it applies to various users, you can see it via the **Permitted Documents for User** report. Using this report, you can select the **User** and document type and check how user permissions get applied.

<img src="{{docs_base_url}}/assets/img/users-and-permissions/user-perms/permitted-documents.png" class="screenshot" alt="Permitted Documents for User report">
