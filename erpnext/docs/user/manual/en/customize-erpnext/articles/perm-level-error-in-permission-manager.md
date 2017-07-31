# Perm Level Error In Permission Manager

#Perm Level Error in Permission Manager

While customizing rules in the [Permission Manager](/docs/user/erpnext/user/manual/en/setting-up/users-and-permissions/role-based-permissions), you might receive an error message saying:

`For System Manager _(or other role)_ at level 2 _(or other level)_ in Customer _(or other document)_ in row 8: Permission at level 0 must be set before higher levels are set.`

Error message indicates problem is in the existing permission setting for this document.

For any role, before assigning permission at Perm Level 1 or 2 (and so on), permission at Perm Level 0 must be assigned. Error message says that System Manager has been assigned permission at Perm Level 1 and 2, but not at level 0. You should first correct the permission for System Manager's role by:

- Assigning permission to System Manager at level 0.

Or

- By removing permission at level 1 and 2.

After executing one of the above step, you should be able to successfully add new permissions rules in the Role Permission Manager.

<!-- markdown -->