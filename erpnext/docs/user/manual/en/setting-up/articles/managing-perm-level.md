<h1>Managing Perm Level in Permission Manager</h1>

<h1>Managing Perm Level in Permission Manager</h1>

In each document, you can group fields by "levels". Each group of field is denoted by a unique number (0, 1, 2, 3 etc.). A separate set of permission rules can be applied to each field group. By default all fields are of level 0.

Perm Level for a field can be defined in the [Customize Form](https://erpnext.com/user-guide/customize-erpnext/customize-form).

![Customize Form]({{docs_base_url}}/assets/img/articles/$SGrab_256.png)

If you need to assign different permission of particular field to different users, you can achieve it via Perm Level. Let's consider an example for better understanding.

Delivery Note is accessible to Stock Manager as well as Stock User. You don't wish Stock User to access Amount related field in Delivery Note, but other field should be visible just like it is visible Stock Manager.

For the amount related fields, you should set Perm Level as (say) 2.

For Stock Manager, they will have permission on fields on Delivery Note as Perm Level 2 whereas a Stock User will not have any permission on Perm Level 2 for Delivery Note.

![Perm Level Manager]({{docs_base_url}}/assets/img/articles/$SGrab_253.png)

Considering the same scenario, if you want a Stock User to access a field at Perm Level 2, but not edit it, the Stock User will be assigned permission on Perm Level 2, but only for read, and not for write/edit.

![Perm Level User]({{docs_base_url}}/assets/img/articles/$SGrab_254.png)

Perm Level (1, 2, 3) not need be in order. Perm Level is primarily for grouping number of fields together, and then assigning permission to Roles for that group. Hence, you can set any perm level for an item, and then do permission setting for it.

<!-- markdown -->
