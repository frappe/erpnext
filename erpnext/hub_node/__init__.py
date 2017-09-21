# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate, cint

@frappe.whitelist()
def enable_hub():
	hub_settings = frappe.get_doc('Hub Settings')
	hub_settings.register()
	frappe.db.commit()
	return hub_settings

@frappe.whitelist()
def get_items(start=0, page_length=20):
	connection = get_connection()
	response = connection.get_list('Hub Item', limit_start=start, limit_page_length=page_length)
	return response.list

@frappe.whitelist()
def get_categories():
	connection = get_connection()
	response = connection.get_list('Hub Category')
	return response.list

# @frappe.whitelist()
# def get_company_details(hub_sync_id):
# 	connection = get_connection()
# 	return connection.get_doc('Hub Company', hub_sync_id)

def get_connection():
	hub_connector = frappe.get_doc(
		'Data Migration Connector', 'Hub Connector')
	hub_connection = hub_connector.get_connection()
	return hub_connection

def get_opportunities_data():
	connection = get_connection()
	hub_settings = frappe.get_doc('Hub Settings')
	response = connection.get_list('Hub Document', fields=['document_data'],
		filters={'type': 'Opportunity', 'user': hub_settings.user})
	data_list = [json.loads(d['document_data']) for d in response.list]
	return data_list

def make_opportunities():
	data_list = get_opportunities_data()
	for d in data_list:
		make_opportunity(d['buyer_name'], d['email_id'])

def make_opportunity(buyer_name, email_id):
	buyer_name = "HUB-" + buyer_name

	if not frappe.db.exists('Lead', {'email_id': email_id}):
		lead = frappe.new_doc("Lead")
		lead.lead_name = buyer_name
		lead.email_id = email_id
		lead.save(ignore_permissions=True)

	o = frappe.new_doc("Opportunity")
	o.enquiry_from = "Lead"
	o.lead = frappe.get_all("Lead", filters={"email_id": email_id}, fields = ["name"])[0]["name"]
	o.save(ignore_permissions=True)

# @frappe.whitelist()
# def get_items(text='', by_item_codes=0, start=0, limit=20, order_by='', category=None, company_name=None, country=None):
# 	item_codes = []
# 	if cint(by_item_codes):
# 		item_codes = [d["item_code"] for d in frappe.get_all("Item", fields=["item_code"], filters={"is_hub_item": "1"},
# 			limit_start = start, limit_page_length = limit)]
# 		if not item_codes:
# 			return []

# 	args = {
# 		"text": text,
# 		"item_codes": item_codes,
# 		"category": category,
# 		"company_name": company_name,
# 		"country": country,
# 		"order_by": order_by,
# 		"start": start,
# 		"limit": limit
# 	}
# 	return hub_request('get_items', data=json.dumps(args))

# @frappe.whitelist()
# def get_all_companies():
# 	return hub_request('get_all_companies')

# @frappe.whitelist()
# def get_item_details(item_code):
# 	args = {
# 		"item_code": item_code,
# 	}
# 	return hub_request('get_item_details', data=json.dumps(args))

# @frappe.whitelist()
# def get_company_details(company_id):
# 	args = {
# 		"company_id": company_id,
# 	}
# 	return hub_request('get_company_details', data=json.dumps(args))

# @frappe.whitelist()
# def get_categories():
# 	# update_local_hub_categories()
# 	return hub_request('get_categories')

# def update_local_hub_categories():
# 	categories = get_categories()
# 	categories_to_remove = []
# 	categories_to_add = []
# 	old_categories = frappe.db.sql_list("select category_name from from `tabHub Category`")
# 	new_categories = [d.category_name for d in categories]
# 	for old_category in old_categories:
# 		if old_category not in new_categories:
# 			categories_to_remove.append(old_category)

# 	for new_category in new_categories:
# 		if new_category not in old_categories:
# 			categories_to_add.append(new_category)

# 	for d in categories_to_remove:
# 		docname = frappe.get_list('Hub Category', filters = {"category_name": d})[0]["name"]
# 		frappe.delete_doc("Hub Category", docname)

# 	for d in categories_to_add:
# 		doc = frappe.new_doc("Hub Category")
# 		doc.category_name = d
# 		doc.save()


# @frappe.whitelist()
# def get_items_seen_states(items):
# 	items = json.loads(items)
# 	for d in items:
# 		local_item_code = "HUB-" + d["item_code"]
# 		if frappe.db.exists("Item", {"item_code": local_item_code}):
# 			d["seen"] = 1
# 		else:
# 			d["seen"] = 0
# 	return items

# @frappe.whitelist()
# def get_local_hub_item_codes():
# 	item_codes = []
# 	for d in frappe.get_all("Item", fields=["item_code"], filters={"is_hub_item": 1}):
# 		item_codes.append(d["item_code"][4:])
# 	return item_codes

@frappe.whitelist()
def hub_item_request_action(item_code, item_group, supplier_name, supplier_email, company, country):
	rfq_made = make_rfq(item_code, item_group, supplier_name, supplier_email, company, country)
	# , send click count and say requested
	send_opportunity_details(supplier_name, supplier_email)
	make_opportunities()
	return rfq_made

def send_opportunity_details(supplier_name, supplier_email):
	connection = get_connection()
	params = {
		"buyer_name": supplier_name,
		"email_id": supplier_email
	}
	args = frappe._dict(dict(
		doctype="Hub Document",
		type="Opportunity",
		document_data=json.dumps(params),
		user=supplier_email
	))
	response = connection.insert("Hub Document", args)

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

	warehouse = frappe.get_list('Warehouse')[0]['name'];
	print(warehouse)

	rfq.append("items", {
		"item_code": item_code,
		"description": item_code,
		"uom": "Nos",
		"qty": 1,
		"warehouse": warehouse, # hardcode, default warehouse for hub items?
		"schedule_date": nowdate()
	})
	rfq.insert(ignore_permissions=True)

	return 1
