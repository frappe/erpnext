# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate

# TESTER
@frappe.whitelist()
def test():
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.test")
	response.raise_for_status()
	return frappe._dict({"message":"sent_rfq_message"})

# @frappe.whitelist()
# def send_rfq_message(website, supplier, supplier_name, email_id, company):
# 	response = requests.get(website + "/api/method/erpnext.hub_node.api.load_message", params={
# 		"supplier": supplier,
# 		"supplier_name": supplier_name,
# 		"email_id": email_id,
# 		"company": company
# 	})
# 	return frappe._dict({"message":"sent_rfq_message"})

# @frappe.whitelist()
# def send_opportunity_message(website, supplier, supplier_name, email_id, company):
# 	response = requests.get(website + "/api/method/erpnext.hub_node.api.load_message", params={
# 		"supplier": supplier,
# 		"supplier_name": supplier_name,
# 		"email_id": email_id,
# 		"company": company
# 	})
# 	return frappe._dict({"message":"sent_opportunity_message"})

@frappe.whitelist()
def load_message(msg_type, receiver, receiver_website, item):
	hub = frappe.get_single("Hub Settings")
	args = json.loads(item)
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.load_message", params={
		"password": hub.password,
		"msg_type": msg_type,
		"sender": hub.hub_user_name,
		"receiver": receiver,
		"receiver_website": receiver_website,
		"msg_data": item
	})
	return frappe._dict({"message":"sent_rfq_message"})



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



### Sender terminal
###

hub = frappe.get_single("Hub Settings")
def make_message_queue_table():
	pass

def call_hub_api_now(method, data):
	response = requests.post(hub.hub_url + "/api/method/hub.hub.api." + method, data=data)
	response.raise_for_status()
	return response.json().get("message")

def store_as_job_message(method, data):
	# encrypt data and store both params in message queue
	pass


### Hub immediately calling api call queries (mirror methods) [direct api call] [wrapper for all: call_hub_api_now]
@frappe.whitelist()
def get_items(text, start, limit, category=None, seller=None):
	return call_hub_api_now('get_items', {
		"password": hub.password,
		"text": text,
		"category": category,
		"seller": seller,
		"start": start,
		"limit": limit
	})

@frappe.whitelist()
def get_all_users():
	return call_hub_api_now('get_all_users', {})

@frappe.whitelist()
def get_categories():
	return call_hub_api_now('get_categories', {})

@frappe.whitelist()
def get_seller_details(user_name):
	return call_hub_api_now('get_user_details', {
		"password": hub.password,
		"user_name": user_name,
	})


### Hub page api calls messages [background] (get message only, don't encrypt) [return .. no store message json in table]
def send_opportunity(website, supplier, supplier_name, email_id, company, now = False):
	# ...
	if not now:
		store_as_job_message(method, data)
	else:
		return call_hub_api_now(method, data)

# def make_rfq_at_seller(website, supplier, supplier_name, email_id, company, now = False):
# 	# ...
# 	if not now:
# 		store_as_job_message(method, data)
# 	else:
# 		return call_hub_api_now(method, data)


### Batch and enqueue module [given table as queue] [table operations: batch]
# call periodically
def batch_and_enqueue_table_operations(): #anytime the table is not empty,
	# and just pick a whole big bunch and enqueue
	# basically, enqueue call_hub_api_now(), but which will instead of returning, store returned status in a log table

	pass

# pick a whole big bunch, query from the table
def get_batch():
	pass
