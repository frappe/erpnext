# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils.make_random import add_random_children, get_random
import frappe.utils

def make_sample_data():
	"""Create a few opportunities, quotes, material requests, issues, todos, projects
	to help the user get started"""

	selling_items = frappe.get_all("Item", filters = {"is_sales_item": "Yes"})
	buying_items = frappe.get_all("Item", filters = {"is_sales_item": "No"})

	if selling_items:
		for i in range(3):
			make_opportunity(selling_items)
			make_quote(selling_items)

	make_projects()

	if buying_items:
		make_material_request(buying_items)

	frappe.db.commit()

def make_opportunity(selling_items):
	b = frappe.get_doc({
		"doctype": "Opportunity",
		"enquiry_from": "Customer",
		"customer": get_random("Customer"),
		"enquiry_type": "Sales",
		"with_items": 1
	})

	add_random_children(b, "items", rows=len(selling_items), randomize = {
		"qty": (1, 5),
		"item_code": ("Item", {"is_sales_item": "Yes"})
	}, unique="item_code")

	b.insert(ignore_permissions=True)

	b.add_comment("This is a dummy record")

def make_quote(selling_items):
	qtn = frappe.get_doc({
		"doctype": "Quotation",
		"quotation_to": "Customer",
		"customer": get_random("Customer"),
		"order_type": "Sales"
	})

	add_random_children(qtn, "items", rows=len(selling_items), randomize = {
		"qty": (1, 5),
		"item_code": ("Item", {"is_sales_item": "Yes"})
	}, unique="item_code")

	qtn.insert(ignore_permissions=True)

	qtn.add_comment("This is a dummy record")

def make_material_request(buying_items):
	for i in buying_items:
		mr = frappe.get_doc({
			"doctype": "Material Request",
			"material_request_type": "Purchase",
			"items": [{
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
				"item_code": i.name,
				"qty": 10
			}]
		})
		mr.insert()
		mr.submit()

		mr.add_comment("This is a dummy record")


def make_issue():
	pass

def make_projects():
	project = frappe.get_doc({
		"doctype": "Project",
		"project_name": "ERPNext Implementation",
	})
	current_date = frappe.utils.nowdate()
	project.set("tasks", [
			{
				"title": "Explore ERPNext",
				"start_date": frappe.utils.add_days(current_date, 1),
				"end_date": frappe.utils.add_days(current_date, 2)
			},
			{
				"title": "Run Sales Cycle",
				"start_date": frappe.utils.add_days(current_date, 2),
				"end_date": frappe.utils.add_days(current_date, 3)
			},
			{
				"title": "Run Billing Cycle",
				"start_date": frappe.utils.add_days(current_date, 3),
				"end_date": frappe.utils.add_days(current_date, 4)
			},
			{
				"title": "Run Purchase Cycle",
				"start_date": frappe.utils.add_days(current_date, 4),
				"end_date": frappe.utils.add_days(current_date, 5)
			},
			{
				"title": "Import Data",
				"start_date": frappe.utils.add_days(current_date, 5),
				"end_date": frappe.utils.add_days(current_date, 6)
			},
			{
				"title": "Go Live!",
				"start_date": frappe.utils.add_days(current_date, 6),
				"end_date": frappe.utils.add_days(current_date, 7)
			}])

	project.insert(ignore_permissions=True)
