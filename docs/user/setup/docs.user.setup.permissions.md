---
{
	"_label": "Setting up Users, Roles and Permissions"
}
---
ERPNext has a role-based permission system, which means that you can assign Roles to Users, and permissions on Roles.

## Users (Profile)

Each ERPNext user has a Profile. The Profile contains the user’s email and authentication and can be set from:

> Setup > Users and Permissions > Users

#### Adding a new User
￼
To add a new user, click on “Add” button and enter the user’s

- Email Id
- First Name
- Last Name
- Password

An invitation email will be sent to the user with the login details.

#### Setting Roles

ERPNext comes with a bunch of predefined roles. Each role comes with predefined permissions. See the Preset Permission Chart to find out what permission each role comes with.

After creating the User, you can add / remove Roles for that User by clicking on “Roles” button. To find out what permission each role has, click on the “?” sign next to the Role.

You can also create new Roles as you wish via

> Document > Role

#### Security Settings

- Enabling / disabling users: You can enable or disable users. Disabled users will not be able to log in.
- Setting login time: If login time is set, users can only log-in within the defined hours as per your timezone.
- Change Password: You can update the user’s password by setting the password field.

## Permissions

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

> **Note 1:** The “match” rules apply to all documents that you have matched by Territory.

> **Note 2:** You can set multiple rules for the same User. In this example, you can set a User to access more than one Territories.
 
