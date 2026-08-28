# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	party_type = filters.get("party_type") or "Customer"
	columns = get_columns(party_type)
	data = get_data(filters, party_type)
	return columns, data


def get_columns(party_type):
	if party_type == "Supplier":
		return [
			{
				"label": _("Supplier Group / Supplier"),
				"fieldname": "name",
				"fieldtype": "Dynamic Link",
				"options": "entity_type",
				"width": 300,
			},
			{
				"label": _("Entity Type"),
				"fieldname": "entity_type",
				"fieldtype": "Data",
				"hidden": 1,
			},
			{
				"label": _("Supplier Type"),
				"fieldname": "supplier_type",
				"fieldtype": "Data",
				"width": 120,
			},
			{
				"label": _("Billing Currency"),
				"fieldname": "default_currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 120,
			},
			{
				"label": _("GST Category"),
				"fieldname": "gst_category",
				"fieldtype": "Data",
				"width": 130,
			},
			{
				"label": _("Is Frozen"),
				"fieldname": "is_frozen",
				"fieldtype": "Check",
				"width": 90,
			},
			{
				"label": _("Blocked"),
				"fieldname": "blocked",
				"fieldtype": "Check",
				"width": 90,
			},
			{
				"label": _("Disabled"),
				"fieldname": "disabled",
				"fieldtype": "Check",
				"width": 90,
			},
		]

	return [
		{
			"label": _("Customer Group / Customer"),
			"fieldname": "name",
			"fieldtype": "Dynamic Link",
			"options": "entity_type",
			"width": 300,
		},
		{
			"label": _("Entity Type"),
			"fieldname": "entity_type",
			"fieldtype": "Data",
			"hidden": 1,
		},
		{
			"label": _("Customer Type"),
			"fieldname": "customer_type",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Billing Currency"),
			"fieldname": "default_currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 120,
		},
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 150,
		},
		{
			"label": _("GST Category"),
			"fieldname": "gst_category",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Disabled"),
			"fieldname": "disabled",
			"fieldtype": "Check",
			"width": 90,
		},
	]


def get_data(filters, party_type):
	if party_type == "Supplier":
		children_map, groups_by_name, parties_by_group = fetch_supplier_group_tree()
		group_filter = filters.get("supplier_group")
	else:
		children_map, groups_by_name, parties_by_group = fetch_customer_group_tree()
		group_filter = filters.get("customer_group")

	if group_filter:
		root = groups_by_name.get(group_filter)
		roots = [root] if root else []
	else:
		roots = get_roots(children_map, groups_by_name)

	build_row = build_supplier_row if party_type == "Supplier" else build_customer_row
	group_doctype = "Supplier Group" if party_type == "Supplier" else "Customer Group"
	party_doctype = party_type

	data = []
	for root in roots:
		build_tree_rows(
			root, children_map, parties_by_group, data, indent=0,
			group_doctype=group_doctype, party_doctype=party_doctype, build_row=build_row,
		)

	return data


def get_roots(children_map, groups_by_name):
	"""Every group with no parent, plus any group whose parent got filtered out
	by user permissions -- otherwise a permitted subtree could become unreachable
	just because an ancestor above it isn't visible to the user.
	"""
	roots = list(children_map.get("", []))
	for parent_name, children in children_map.items():
		if parent_name and parent_name not in groups_by_name:
			roots.extend(children)

	return sorted(roots, key=lambda group: group.name)


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

	fields = ["name", "customer_name", "customer_group", "customer_type", "territory", "default_currency", "disabled"]
	if frappe.get_meta("Customer").has_field("gst_category"):
		fields.append("gst_category")

	customers = frappe.get_list("Customer", fields=fields)

	customers_by_group = {}
	for customer in customers:
		customers_by_group.setdefault(customer.customer_group or "", []).append(customer)

	return children_map, groups_by_name, customers_by_group


def fetch_supplier_group_tree():
	"""Same idea as `fetch_customer_group_tree`, but for Supplier Group / Supplier."""
	supplier_groups = frappe.get_list(
		"Supplier Group",
		fields=["name", "parent_supplier_group"],
	)

	children_map = {}
	groups_by_name = {}
	for group in supplier_groups:
		children_map.setdefault(group.parent_supplier_group or "", []).append(group)
		groups_by_name[group.name] = group

	fields = [
		"name",
		"supplier_name",
		"supplier_group",
		"supplier_type",
		"default_currency",
		"is_frozen",
		"on_hold",
		"disabled",
	]
	if frappe.get_meta("Supplier").has_field("gst_category"):
		fields.append("gst_category")

	suppliers = frappe.get_list("Supplier", fields=fields)

	suppliers_by_group = {}
	for supplier in suppliers:
		suppliers_by_group.setdefault(supplier.supplier_group or "", []).append(supplier)

	return children_map, groups_by_name, suppliers_by_group


def build_customer_row(customer):
	return {
		"customer_type": customer.customer_type,
		"default_currency": customer.default_currency,
		"territory": customer.territory,
		"gst_category": customer.get("gst_category"),
		"disabled": customer.disabled,
	}


def build_supplier_row(supplier):
	return {
		"supplier_type": supplier.supplier_type,
		"default_currency": supplier.default_currency,
		"gst_category": supplier.get("gst_category"),
		"is_frozen": supplier.is_frozen,
		"blocked": supplier.on_hold,
		"disabled": supplier.disabled,
	}


def build_tree_rows(group, children_map, parties_by_group, data, indent, group_doctype, party_doctype, build_row):
	data.append(
		{
			"name": group.name,
			"entity_type": group_doctype,
			"indent": indent,
		}
	)

	child_groups = sorted(children_map.get(group.name, []), key=lambda child: child.name)
	for child_group in child_groups:
		build_tree_rows(
			child_group, children_map, parties_by_group, data, indent + 1,
			group_doctype=group_doctype, party_doctype=party_doctype, build_row=build_row,
		)

	party_name_field = "customer_name" if party_doctype == "Customer" else "supplier_name"
	parties = sorted(
		parties_by_group.get(group.name, []),
		key=lambda party: party.get(party_name_field) or party.name,
	)
	for party in parties:
		row = {"name": party.name, "entity_type": party_doctype, "indent": indent + 1}
		row.update(build_row(party))
		data.append(row)
