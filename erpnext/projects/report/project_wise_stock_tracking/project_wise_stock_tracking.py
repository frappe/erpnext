# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, NullIf, Sum


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

	pi = frappe.qb.DocType("Purchase Invoice")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")
	pi_items = (
		frappe.qb.from_(pi)
		.inner_join(pi_item)
		.on(pi.name == pi_item.parent)
		.select(pi_item.project, Sum(pi_item.base_net_amount).as_("amount"))
		.where((pi.docstatus == 1) & (pi.update_stock == 1) & (pi_item.project != ""))
		.groupby(pi_item.project)
		.run(as_dict=1)
	)

	return sum_amount_by_project(pr_items + pi_items)


def get_issued_items_cost():
	se = frappe.qb.DocType("Stock Entry")
	se_item = frappe.qb.DocType("Stock Entry Detail")
	project = Coalesce(NullIf(se_item.project, ""), se.project)
	se_items = (
		frappe.qb.from_(se)
		.inner_join(se_item)
		.on(se.name == se_item.parent)
		.select(project.as_("project"), Sum(se_item.amount).as_("amount"))
		.where(
			(se.docstatus == 1)
			& (se_item.t_warehouse.isnull() | (se_item.t_warehouse == ""))
			& (project != "")
		)
		.groupby(project)
		.run(as_dict=1)
	)

	se_item_map = {}
	for item in se_items:
		se_item_map.setdefault(item.project, item.amount)

	return se_item_map


def get_delivered_items_cost():
	sle = frappe.qb.DocType("Stock Ledger Entry")
	dn_item = frappe.qb.DocType("Delivery Note Item")
	si_item = frappe.qb.DocType("Sales Invoice Item")
	project = Coalesce(NullIf(dn_item.project, ""), NullIf(si_item.project, ""), sle.project)
	return dict(
		frappe.qb.from_(sle)
		.left_join(dn_item)
		.on((sle.voucher_type == "Delivery Note") & (dn_item.name == sle.voucher_detail_no))
		.left_join(si_item)
		.on((sle.voucher_type == "Sales Invoice") & (si_item.name == sle.voucher_detail_no))
		.select(project, -Sum(sle.stock_value_difference))
		.where(
			sle.voucher_type.isin(["Delivery Note", "Sales Invoice"])
			& (sle.is_cancelled == 0)
			& (project != "")
		)
		.groupby(project)
		.run()
	)


def sum_amount_by_project(rows):
	amounts = {}
	for row in rows:
		amounts[row.project] = amounts.get(row.project, 0) + row.amount

	return amounts
