# Difference Between System User and Website User

**Question:** I have added my Employee as a User and have assigned them Roles as well. Still, they are not able to view Dashboard on the login.

**Answer:**

There are two type of Users in ERPNext.

* **System User**: They are Employees of your company. Example of Roles assigned to System Users are Account User, Sales Manager, Purchase User, Support Team etc.

* **Website User**: They are to parties (like Customer and Suppliers) of your Company. 

Example Website User Roles are Customer and Suppliers.

How to check if Role is for System User or Website User?

In the Role master, if field "Desk Access" is checked, that Role is for System User. If Desk Access field is unchecked, then that Role is for Website User.

<img alt="Role Desk Permission" class="screenshot" src="/docs/assets/img/articles/role-deskperm.png">