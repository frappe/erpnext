# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests

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

@frappe.whitelist()
def send_rfq():
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.send_rfq")
	response.raise_for_status()
	return frappe._dict({"message":"sent_rfq_message"})

@frappe.whitelist()
def send_rfq_message(website, supplier, supplier_name, email_id, company):
	response = requests.get(website + "/api/method/erpnext.hub_node.api.load_message", params={
		"supplier": supplier,
		"supplier_name": supplier_name,
		"email_id": email_id,
		"company": company
	})
	return frappe._dict({"message":"sent_rfq_message"})

@frappe.whitelist()
def send_opportunity_message(website, supplier, supplier_name, email_id, company):
	response = requests.get(website + "/api/method/erpnext.hub_node.api.load_message", params={
		"supplier": supplier,
		"supplier_name": supplier_name,
		"email_id": email_id,
		"company": company
	})
	return frappe._dict({"message":"sent_opportunity_message"})