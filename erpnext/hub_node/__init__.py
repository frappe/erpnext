# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate
from erpnext.hub_node.doctype.hub_settings.hub_settings import hub_request

opp_msg_id = ""

@frappe.whitelist()
def get_items(text, start, limit, category=None, company_name=None, country=None):
	args = {
		"text": text,
		"category": category,
		"company_name": company_name,
		"country": country,
		"start": start,
		"limit": limit
	}
	return hub_request('get_items', data=json.dumps(args))

@frappe.whitelist()
def get_all_companies():
	return hub_request('get_all_companies')

@frappe.whitelist()
def get_item_details(item_code):
	args = {
		"item_code": item_code,
	}
	return hub_request('get_item_details', data=json.dumps(args))

@frappe.whitelist()
def get_company_details(company_id):
	args = {
		"company_id": company_id,
	}
	return hub_request('get_company_details', data=json.dumps(args))

@frappe.whitelist()
def get_categories():
	return hub_request('get_categories')

def update_local_hub_categories():
	categories = get_categories()
	categories_to_remove = []
	categories_to_add = []
	old_categories = frappe.db.sql_list("select category_name from from `tabHub Category`")
	new_categories = [d.category_name for d in categories]
	for old_category in old_categories:
		if old_category not in new_categories:
			categories_to_remove.append(old_category)

	for new_category in new_categories:
		if new_category not in old_categories:
			categories_to_add.append(new_category)

	for d in categories_to_remove:
		docname = frappe.get_list('Hub Category', filters = {"category_name": d})[0]["name"]
		frappe.delete_doc("Hub Category", docname)

	for d in categories_to_add:
		doc = frappe.new_doc("Hub Category")
		doc.category_name = d
		doc.save()

@frappe.whitelist()
def hub_item_request_action(item_code, item_group, supplier_name, supplier_email, company, country):
	# make rfq, send click count and say requested
	# enqueue opportunity message
	pass

@frappe.whitelist()
def make_rfq_and_send_opportunity(item_code, item_group, supplier_name, supplier_email, company, country):
	rfq_made = make_rfq(item_code, item_group, supplier_name, supplier_email, company, country)
	opportunity_sent = send_opportunity(supplier_name, supplier_email)
	return rfq_made and opportunity_sent

@frappe.whitelist()
def request_opportunity_message_status():
	# needs an outgoing hub message
	return hub_request('get_message_status', data={
		"message_id": "CLIENT-OPP-"
	})

def send_opportunity(supplier_name, supplier_email):
	args = {
		"buyer_name": supplier_name,
		"email_id": supplier_email
	}
	opp_msg_id = hub_request('enqueue_message', data={
		"message_type": "CLIENT-OPP-",
		"method": "make_opportunity",
		"arguments": json.dumps(args),
		"receiver_email": supplier_email
	})

	return opp_msg_id

def make_rfq(item_code, item_group, supplier_name, supplier_email, company, country):
	item_code = "HUB-" + item_code
	supplier_name = "HUB-" + supplier_name
	company = "HUB-" + company

	if not frappe.db.exists('Supplier', {'supplier_name': supplier_name}):
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = supplier_name
		supplier.supplier_type = "Distributor"
		supplier.insert(ignore_permissions = True)

	if not frappe.db.exists('Item', {'item_code': item_code}):
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

	return 1
