# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils.make_random import add_random_children
import frappe.utils
import random

def make_sample_data():
	"""Create a few opportunities, quotes, material requests, issues, todos, projects
	to help the user get started"""
	items = frappe.get_all("Item")

	customers = frappe.get_all("Customer")
	warehouses = frappe.get_all("Warehouse")

	if items and customers:
		for i in range(3):
			customer = random.choice(customers).name
			make_opportunity(items, customer)
			make_quote(items, customer)

	make_projects()

	if items and warehouses:
		make_material_request(items)

	frappe.db.commit()

def make_opportunity(items, customer):
	b = frappe.get_doc({
		"doctype": "Opportunity",
		"enquiry_from": "Customer",
		"customer": customer,
		"enquiry_type": "Sales",
		"with_items": 1
	})

	add_random_children(b, "items", rows=len(items), randomize = {
		"qty": (1, 5),
		"item_code": ["Item"]
	}, unique="item_code")

	b.insert(ignore_permissions=True)

	b.add_comment('Comment', text="This is a dummy record")

def make_quote(items, customer):
	qtn = frappe.get_doc({
		"doctype": "Quotation",
		"quotation_to": "Customer",
		"customer": customer,
		"order_type": "Sales"
	})

	add_random_children(qtn, "items", rows=len(items), randomize = {
		"qty": (1, 5),
		"item_code": ["Item"]
	}, unique="item_code")

	qtn.insert(ignore_permissions=True)

	qtn.add_comment('Comment', text="This is a dummy record")

def make_material_request(items):
	for i in items:
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

		mr.add_comment('Comment', text="This is a dummy record")


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
