# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests

@frappe.whitelist()
def get_items(text, start, limit):
	hub = frappe.get_single("Hub Settings")
	response = requests.get(hub.hub_url + "/api/method/hub.hub.api.get_items", params={
		"access_token": hub.access_token,
		"text": text,
		"start": start,
		"limit": limit
	})
	response.raise_for_status()
	return response.json().get("message")
