# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


def execute(filters=None):
	columns = get_columns()
	proj_details = get_project_details()
	pr_item_map = get_purchased_items_cost()
	se_item_map = get_issued_items_cost()
	dn_item_map = get_delivered_items_cost()

	data = []
	for project in proj_details:
		data.append(
			[
				project.name,
				pr_item_map.get(project.name, 0),
				se_item_map.get(project.name, 0),
				dn_item_map.get(project.name, 0),
				project.project_name,
				project.status,
				project.company,
				project.customer,
				project.estimated_costing,
				project.expected_start_date,
				project.expected_end_date,
			]
		)

	return columns, data


def get_columns():
	return [
		_("Project Id") + ":Link/Project:140",
		_("Cost of Purchased Items") + ":Currency:160",
		_("Cost of Issued Items") + ":Currency:160",
		_("Cost of Delivered Items") + ":Currency:160",
		_("Project Name") + "::120",
		_("Project Status") + "::120",
		_("Company") + ":Link/Company:100",
		_("Customer") + ":Link/Customer:140",
		_("Project Value") + ":Currency:120",
		_("Project Start Date") + ":Date:120",
		_("Completion Date") + ":Date:120",
	]


def get_project_details():
	return frappe.get_all(
		"Project",
		filters={"docstatus": ["<", 2]},
		fields=[
			"name",
			"project_name",
			"status",
			"company",
			"customer",
			"estimated_costing",
			"expected_start_date",
			"expected_end_date",
		],
	)


def get_purchased_items_cost():
	pr_items = frappe.get_all(
		"Purchase Receipt Item",
		filters={"project": ["is", "set"], "docstatus": 1},
		fields=["project", {"SUM": "base_net_amount", "as": "amount"}],
		group_by="project",
	)

	pr_item_map = {}
	for item in pr_items:
		pr_item_map.setdefault(item.project, item.amount)

	return pr_item_map


def get_issued_items_cost():
	se = frappe.qb.DocType("Stock Entry")
	se_item = frappe.qb.DocType("Stock Entry Detail")
	se_items = (
		frappe.qb.from_(se)
		.inner_join(se_item)
		.on(se.name == se_item.parent)
		.select(se.project, Sum(se_item.amount).as_("amount"))
		.where(
			(se.docstatus == 1)
			& (se_item.t_warehouse.isnull() | (se_item.t_warehouse == ""))
			& (se.project != "")
		)
		.groupby(se.project)
		.run(as_dict=1)
	)

	se_item_map = {}
	for item in se_items:
		se_item_map.setdefault(item.project, item.amount)

	return se_item_map


def get_delivered_items_cost():
	dn = frappe.qb.DocType("Delivery Note")
	dn_item = frappe.qb.DocType("Delivery Note Item")
	dn_items = (
		frappe.qb.from_(dn)
		.inner_join(dn_item)
		.on(dn.name == dn_item.parent)
		.select(dn.project, Sum(dn_item.base_net_amount).as_("amount"))
		.where((dn.docstatus == 1) & (dn.project != ""))
		.groupby(dn.project)
		.run(as_dict=1)
	)

	si = frappe.qb.DocType("Sales Invoice")
	si_item = frappe.qb.DocType("Sales Invoice Item")
	si_items = (
		frappe.qb.from_(si)
		.inner_join(si_item)
		.on(si.name == si_item.parent)
		.select(si.project, Sum(si_item.base_net_amount).as_("amount"))
		.where((si.docstatus == 1) & (si.update_stock == 1) & (si.is_pos == 1) & (si.project != ""))
		.groupby(si.project)
		.run(as_dict=1)
	)

	dn_item_map = {}
	for item in dn_items:
		dn_item_map.setdefault(item.project, item.amount)

	for item in si_items:
		dn_item_map.setdefault(item.project, item.amount)

	return dn_item_map
