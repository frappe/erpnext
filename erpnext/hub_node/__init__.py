# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate
from erpnext.hub_node.doctype.hub_settings.hub_settings import call_hub_api_now

@frappe.whitelist()
def get_items(text, start, limit, category=None, company=None, country=None):
	return call_hub_api_now('get_items', data={
		"text": text,
		"category": category,
		"company": company,
		"country": country,
		"start": start,
		"limit": limit
	})

@frappe.whitelist()
def get_all_users():
	return call_hub_api_now('get_all_users')

@frappe.whitelist()
def get_categories():
	return call_hub_api_now('get_categories')

@frappe.whitelist()
def get_all_companies():
	return call_hub_api_now('get_all_companies')

@frappe.whitelist()
def get_seller_details(user_name):
	return call_hub_api_now('get_user_details', data={
		"user_name": user_name,
	})

@frappe.whitelist()
def make_rfq(item_code, item_group, supplier_name, supplier_email, company):
	args = {
		"buyer_name": "Susan",
		"email_id": "susan@example.com"
	}

	response = requests.post("http://erpnext.user1:8000" + "/api/method/erpnext.hub_node.api.make_opportunity", data=json.dumps(args))
	response.raise_for_status()
	return response.json().get("message")

	if not frappe.db.exists('Supplier', {'supplier_name': supplier_name}):
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = supplier_name
		supplier.supplier_type = "Distributor"
		supplier.insert(ignore_permissions = True)

	if not frappe.db.exists('Item', {'item_code': item_code}):
		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_group = item_group
		item.insert(ignore_permissions = True)

	if not frappe.db.exists('Company', {'company_name': company}):
		comp = frappe.new_doc("Company")
		comp.company_name = company
		comp.abbr = "hub" + company[0]
		comp.domain = "Distribution"
		comp.country = "India"
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
		"warehouse": "Stores - F",
		"schedule_date": nowdate()
	})
	rfq.insert(ignore_permissions=True)
