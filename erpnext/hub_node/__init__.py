# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate
from erpnext.hub_node.doctype.hub_settings.hub_settings import send_hub_request

@frappe.whitelist()
def get_items(text, start, limit, category=None, company=None, country=None):
	return send_hub_request('get_items', data={
		"text": text,
		"category": category,
		"company": company,
		"country": country,
		"start": start,
		"limit": limit
	})

@frappe.whitelist()
def get_all_users():
	return send_hub_request('get_all_users')

@frappe.whitelist()
def get_categories():
	return send_hub_request('get_categories')

@frappe.whitelist()
def get_all_companies():
	return send_hub_request('get_all_companies')

@frappe.whitelist()
def get_seller_details(user_name):
	return send_hub_request('get_user_details', data={
		"user_name": user_name,
	})

@frappe.whitelist()
def make_rfq(item_code, item_group, supplier_name, supplier_email, company, country):
	item_code = "HUB-" + item_code
	supplier_name = "HUB-" + supplier_name
	company = "HUB-" + company

	# return if item_code already exists
	if frappe.db.exists("Item", {'item_code': item_code}):
		return "Fail: Already exists"

	if not frappe.db.exists('Supplier', {'supplier_name': supplier_name}):
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = supplier_name
		supplier.supplier_type = "Distributor"
		supplier.insert(ignore_permissions = True)

	item = frappe.new_doc("Item")
	item.item_code = item_code
	item.item_group = item_group
	item.is_hub_item = 1
	item.insert(ignore_permissions = True)

	if not frappe.db.exists('Company', {'company_name': company}):
		comp = frappe.new_doc("Company")
		comp.company_name = company
		comp.abbr = "HUB-" + company[0]
		comp.domain = "Distribution"
		comp.country = country
		comp.default_currency = "USD"
		comp.insert(ignore_permissions = True)

	supplier_data = {
		"supplier": supplier_name,
		"supplier_name": supplier_name,
		"email_id": supplier_email
	}

	rfq = frappe.new_doc('Request for Quotation')
	rfq.transaction_date = nowdate()
	rfq.status = 'Draft'
	rfq.company = company
	rfq.message_for_supplier = 'Please supply the specified items at the best possible rates.'

	rfq.append('suppliers', supplier_data)

	rfq.append("items", {
		"item_code": item_code,
		"description": item_code,
		"uom": "Nos",
		"qty": 1,
		"warehouse": "Stores - F", # hardcode, default warehouse for hub items?
		"schedule_date": nowdate()
	})
	rfq.insert(ignore_permissions=True)

	return "Success"
