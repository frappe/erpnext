<h1>ERPNext for Service Organizations</h1>

**Question:** At first look, ERPNext looks primarily designed for the traders and manufacturers. Is ERPNext used by service companies as well?

**Answer:**
About 30% of ERPNext customers comes from services background. These are companies into software development, certification services, individual consultants and many more. Being into services business ourselves, we use ERPNext to manage our sales, accounting, support and HR operations.

https://conf.erpnext.com/2014/videos/umair-sayyed

###Master Setup

Between the service and trading company, the most differentiating master is an item master. While trading and manufacturing business has stock item, with warehouse and other stock details, service items will have none of these details.

To create a services item, which will be non-stock item, in the Item master, you should set "Is Stock Item" field as "No".

![non-stock item]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-01 at 5.32.57 pm.png)

###Hiding Non-required Features

####Feature Setup

In Feature Setup, you can activate specific functionalities, and disable others. Based on this setting, forms and fields not required for your business will be hidden. [More on feature setup here](https://manual.erpnext.com/customize-erpnext/hiding-modules-and-features).

####Permissions

ERPNext is the permission driven system. User will be able to access system based on permissions assigned to him/her. So, if user is not assigned Role related to Stock and Manufacturing module, it will be hidden from user. [More on permission management in ERPNext here](https://manual.erpnext.com/setting-up/users-and-permissions).

<!-- markdown -->