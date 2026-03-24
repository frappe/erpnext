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
		filters={"docstatus": ["<", 2]},
	)


def get_purchased_items_cost():
	pr_items = frappe.get_all(
		"Purchase Receipt Item",
		filters=[["project", "!=", ""], ["docstatus", "=", 1]],
		fields=["project", "sum(base_net_amount) as amount"],
		group_by="project",
	)

	pr_item_map = {}
	for item in pr_items:
		pr_item_map.setdefault(item.project, item.amount)

	return pr_item_map


def get_issued_items_cost():
	stock_entry = frappe.qb.DocType("Stock Entry")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
	se_items = (
		frappe.qb.from_(stock_entry_detail)
		.join(stock_entry)
		.on(stock_entry.name == stock_entry_detail.parent)
		.select(stock_entry.project, Sum(stock_entry_detail.amount).as_("amount"))
		.where(
			(stock_entry.docstatus == 1)
			& ((stock_entry_detail.t_warehouse.isnull()) | (stock_entry_detail.t_warehouse == ""))
			& (stock_entry.project != "")
		)
		.groupby(stock_entry.project)
	).run(as_dict=True)

	se_item_map = {}
	for item in se_items:
		se_item_map.setdefault(item.project, item.amount)

	return se_item_map


def get_delivered_items_cost():
	delivery_note = frappe.qb.DocType("Delivery Note")
	delivery_note_item = frappe.qb.DocType("Delivery Note Item")
	dn_items = (
		frappe.qb.from_(delivery_note_item)
		.join(delivery_note)
		.on(delivery_note.name == delivery_note_item.parent)
		.select(delivery_note.project, Sum(delivery_note_item.base_net_amount).as_("amount"))
		.where((delivery_note.docstatus == 1) & (delivery_note.project != ""))
		.groupby(delivery_note.project)
	).run(as_dict=True)

	sales_invoice = frappe.qb.DocType("Sales Invoice")
	sales_invoice_item = frappe.qb.DocType("Sales Invoice Item")
	si_items = (
		frappe.qb.from_(sales_invoice_item)
		.join(sales_invoice)
		.on(sales_invoice.name == sales_invoice_item.parent)
		.select(sales_invoice.project, Sum(sales_invoice_item.base_net_amount).as_("amount"))
		.where(
			(sales_invoice.docstatus == 1)
			& (sales_invoice.update_stock == 1)
			& (sales_invoice.is_pos == 1)
			& (sales_invoice.project != "")
		)
		.groupby(sales_invoice.project)
	).run(as_dict=True)

	dn_item_map = {}
	for item in dn_items:
		dn_item_map.setdefault(item.project, item.amount)

	for item in si_items:
		dn_item_map.setdefault(item.project, item.amount)

	return dn_item_map
