<h1>Perm Level Error in Permission Manager</h1>

While customizing rules in the [Permission Manager](https://erpnext.com/user-guide/setting-up/permissions/role-based-permissions), you might receive an error message saying:

`For System Manager_ (or other role) _at level 2_ (or other level) _in Customer_ (or document) _in row 8: Permission at level 0 must be set before higher levels are set`.

Error message indicates problem in the existing permission setting for this document.

For any role, before assigning permission at Perm Level 1, 2, permission at Perm Level 0 must be assigned. Error message says that System Manager has been assigned permission at Perm Level 1 and 2, but not at level 0. You should first correct the permission for System Manager's role by:

- Assigning permission to System Manager at level 0.

Or

- By removing permission at level 1 and 2.

After executing one of the above step, you should try adding additional rules in the Role Permission Manager.

<!-- markdown -->