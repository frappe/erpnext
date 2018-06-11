# Supplier Group

A supplier may be distinguished from a contractor or subcontractor, who
commonly adds specialized input to deliverables. A supplier is also known as a
vendor. There are different types of suppliers based on their goods and
products.

ERPNext allows you to create your own categories of suppliers. These
categories are known as Supplier Groups. For example, if your suppliers are
mainly pharmaceutical companies and FMCG distributors, you can create a new
type for them and name them accordingly.

Based on what the suppliers supply, they are classified into different
Supplier Groups. You can create your own category of Supplier Group.

> Buying > Setup > Supplier Group > New Supplier Group

<img class="screenshot" alt="Supplier Group" src="{{docs_base_url}}/assets/img/buying/supplier-group.png">

You can classify your suppliers from a range of choices available in ERPNext.
Choose from a set of given options like Distributor, Electrical, Hardware,
Local, Pharmaceutical, Raw material, Services etc.

Classifying your supplier into different types facilitates accounting and
payments.

Type your new supplier category and Save.

## Supplier Group Tree

You can also construct Supplier Group in the form of a tree hierarchy, similar
to that of Chart of Accounts.

To view the Tree structure, select `tree` from the sidebar. To go back to the
list view, simply select `Menu > View List`.

<img class="screenshot" alt="Supplier Group" src="{{docs_base_url}}/assets/img/buying/supplier-group-tree.png">

With the new [User Permission](https://erpnext.org/docs/user/manual/en/setting-up/users-and-permissions)
in place, you can now apply hierarchy based permissions.
That is, if a User is permitted to view parent node of Supplier Group,
he/she automatically qualifies to view the child nodes of that parent node.

Example, in the above image, let's say that user permission is applied for a User to
view 'Distributor' document. Then the user also gets permitted to view its
child nodes 'Book Distributor', 'Electronic Distributor', etc.
