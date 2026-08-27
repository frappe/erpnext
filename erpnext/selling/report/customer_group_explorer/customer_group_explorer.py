# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Customer Group / Customer"),
			"fieldname": "name",
			"fieldtype": "Dynamic Link",
			"options": "entity_type",
			"width": 300,
		},
		{
			"label": _("Type"),
			"fieldname": "entity_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Under Customer Group"),
			"fieldname": "parent_customer_group",
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": 180,
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 150,
		},
		{
			"label": _("Level"),
			"fieldname": "level",
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"label": _("Disabled"),
			"fieldname": "disabled",
			"fieldtype": "Check",
			"width": 90,
		},
	]


def get_data(filters):
	children_map, groups_by_name, customers_by_group = fetch_customer_group_tree()

	if filters.get("customer_group"):
		root = groups_by_name.get(filters.customer_group)
		roots = [root] if root else []
	else:
		roots = sorted(children_map.get("", []), key=lambda group: group.name)

	data = []
	for root in roots:
		build_tree_rows(root, children_map, customers_by_group, data, indent=0)

	return data


def fetch_customer_group_tree():
	"""Group every Customer Group by its parent, and every Customer by its
	Customer Group, so the tree can be walked without repeated DB round-trips.

	Uses `get_list` (not `get_all`) so that user permissions on Customer are
	respected -- a Sales User restricted to specific customers must not see
	customers outside their permitted scope in this report.
	"""
	customer_groups = frappe.get_list(
		"Customer Group",
		fields=["name", "parent_customer_group"],
	)

	children_map = {}
	groups_by_name = {}
	for group in customer_groups:
		children_map.setdefault(group.parent_customer_group or "", []).append(group)
		groups_by_name[group.name] = group

	customers = frappe.get_list(
		"Customer",
		fields=["name", "customer_name", "customer_group", "territory", "disabled"],
	)

	customers_by_group = {}
	for customer in customers:
		customers_by_group.setdefault(customer.customer_group or "", []).append(customer)

	return children_map, groups_by_name, customers_by_group


def build_tree_rows(group, children_map, customers_by_group, data, indent):
	data.append(
		{
			"name": group.name,
			"entity_type": "Customer Group",
			"parent_customer_group": group.parent_customer_group,
			"territory": None,
			"level": indent,
			"indent": indent,
			"disabled": None,
		}
	)

	child_groups = sorted(children_map.get(group.name, []), key=lambda child: child.name)
	for child_group in child_groups:
		build_tree_rows(child_group, children_map, customers_by_group, data, indent + 1)

	customers = sorted(
		customers_by_group.get(group.name, []), key=lambda customer: customer.customer_name or customer.name
	)
	for customer in customers:
		data.append(
			{
				"name": customer.name,
				"entity_type": "Customer",
				"parent_customer_group": customer.customer_group,
				"territory": customer.territory,
				"level": indent + 1,
				"indent": indent + 1,
				"disabled": customer.disabled,
			}
		)
