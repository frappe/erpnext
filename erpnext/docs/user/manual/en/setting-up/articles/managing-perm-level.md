# Managing Perm Level

#Managing Perm Level in Permission Manager

In each document, you can group fields by "levels". Each group of field is denoted by a unique number (0, 1, 2, 3 etc.). A separate set of permission rules can be applied to each field group. By default all fields are of level 0.

Perm Level for a field can be defined in the [Customize Form]({{docs_base_url}}/user/manual/en/customize-erpnext/customize-form.html).

<img alt="Perm Level Field" class="screenshot" src="{{docs_base_url}}/assets/img/articles/perm-level-1.gif">

If you need to assign different permission of particular field to different users, you can achieve it via Perm Level. Let's consider an example for better understanding.

Delivery Note is accessible to Stock Manager as well as Stock User. You don't wish Stock User to access Amount related field in Delivery Note, but other field should be visible just like it is visible Stock Manager.

For the amount related fields, you should set Perm Level as (say) 2.

For Stock Manager, they will have permission on fields on Delivery Note as Perm Level 2 whereas a Stock User will not have any permission on Perm Level 2 for Delivery Note.

<img alt="Perm Level Rule" class="screenshot" src="{{docs_base_url}}/assets/img/articles/perm-level-2.png">

Considering the same scenario, if you want a Stock User to access a field at Perm Level 2, but not edit it, the Stock User will be assigned permission on Perm Level 2, but only for read, and not for write/edit.

<img alt="Perm Level Rule 2" class="screenshot" src="{{docs_base_url}}/assets/img/articles/perm-level-3.png">

Perm Level (1, 2, 3) not need be in order. Perm Level is primarily for grouping number of fields together, and then assigning permission to Roles for that group. Hence, you can set any perm level for an item, and then do permission setting for it.

<!-- markdown -->
