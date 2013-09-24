---
{
	"_label": "Setting up Permissions"
}
---
ERPNext has a role-based permission system, which means that you can assign Roles to Users, and Permissions on Roles.

ERPNext has a very powerful permission structure that will allow you to set permissions right up to the field level.

Permissions are applied on:

- **Roles:** As we saw earlier, Users are assigned to Roles and it is on these Roles that permission rules are applied.￼
- **Document Types:** Each type of document, master or transaction, has a separate list of Role based permission.
- **Document Stages:** Permissions are applied on each stage of the document like on Creation, Saving, Submission, Cancellation and Amendment. 
- **Permission “Levels”:** In each document, you can group fields by “levels”. Each group of field is denoted by a unique number (1,2,3 etc.). A separate set of permission rules can be applied to each field group. By default all fields are of level 0.
- **“Match Rules”** Based on certain properties of the document and the user: This can be used in cases where, for example, you have multiple Companies or sales persons in different Territories and you want to restrict each User to only view documents relating to the User’s Company or Territory etc. It is also called “match” rules.

When you define a “match” rule, the User will only be allowed to access (or write) the document if the User has one or more such values (e.g. Company, Territories) and the document has the same values.   For example, if you have set a match rule on Sales Order for a particular Role based on “territory”, then all users of that Role will only be allowed to view Sales Orders of that Territory. Let us walk through an example.

ERPNext comes with pre-set permission rules that you can change anytime by going to

> Setup > Users and Permissions > Permission Manager

![Permission Manager](img/permission-manager.png)




## Using the Permission Manager

The Permission Manager is an easy way to set / unset permission rules. The Permission Manager allows you to monitor rules per Document Type.

When you select a document type from the drop-down. You will see the rules that have already been applied.

To add a new rule, click on “Add a New Rule” button and a pop-up box will ask you to select a Role and a Permission Level. Once you select this and click on “Add”, this will add a new row to your rules table.

To edit rules, just check or uncheck the boxes stating the permission level and Role and click on “Update”.

To delete a rule, just uncheck all the boxes of the row and click on “Update” 

To set “match” rules, select the drop-down in the last column.  For example, you want to restrict Users of Role “Sales User” by Territories in Sales Order. 


1. Select Sales Order in “Set Permissions For”
1. In the row for Role “Sales User”, in the last column “Restrict By”, select “territory”.
1. To assign Territories to Users, click on “Set Users / Roles”
1. In the popup box, 
	- In the “Who” column, select “Profile” and the User you want to assign the Territory to
	- In the “Is allowed if territory equals” column, select the Territory you want to assign 	to this user.
1. Click on “Add”

In the same way, add a row for each user.

#### Step 1: Select Sales Order in "Set Permissions For"


![Permissions Manager](img/permission-manager-1.png)

#### Step 2: Select restriction option as Territory

<br>
![Permissions Manager](img/permission-manager-2.png)

<br>

#### Step 3: To assign Territories to users, click on "Set Users/Roles"

<br>

![Permissions Manager](img/permission-manager-3.png)


#### Step 3: Restrict User by selecting Territory


![Permission Manager](img/permission-manager-4.png)


#### Step 4: Select the User to assign to a Territory


![Permission Manager](img/permission-manager-5.png)


> **Note 1:** The “match” rules apply to all documents that you have matched by Territory.

> **Note 2:** You can set multiple rules for the same User. In this example, you can set a User to access more than one Territories.
 

If you have more than two companies, we recommend that you should maintain seperate databases for these companies (2/3 ERPnext accounts). This avoids data leak from one company to another.

