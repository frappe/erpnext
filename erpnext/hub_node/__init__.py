# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json

@frappe.whitelist()
def get_items(text, start, limit, category=None, seller=None):
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.get_items", params={
		"password": hub.password,
		"text": text,
		"category": category,
		"seller": seller,
		"start": start,
		"limit": limit
	})
	response.raise_for_status()
	return response.json().get("message")

@frappe.whitelist()
def get_all_users():
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.get_all_users")
	response.raise_for_status()
	return response.json().get("message")

@frappe.whitelist()
def get_categories():
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.get_categories")
	response.raise_for_status()
	return response.json().get("message")

@frappe.whitelist()
def get_seller_details(user_name):
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.get_user_details", params={
		"password": hub.password,
		"user_name": user_name,
	})
	response.raise_for_status()
	return response.json().get("message")

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