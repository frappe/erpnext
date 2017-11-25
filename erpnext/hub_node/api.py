# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe, json
from frappe.utils import now, nowdate
from erpnext.hub_node.doctype.hub_settings.hub_settings import get_hub_settings

# API wrapper
@frappe.whitelist(allow_guest=True)
def call_method(access_token, method, message):
	try:
		args = json.loads(message)
		if args:
			return globals()[method](access_token, args)
		else:
			return globals()[method](access_token)
	except:
		print("Client Exception")
		print(frappe.get_traceback())

def disable_and_suspend_hub_user(access_token):
	hub_settings = get_hub_settings()
	hub_settings.publish = 0
	hub_settings.publish_pricing = 0
	hub_settings.publish_availability = 0
	hub_settings.suspended = 1
	hub_settings.enabled = 0
	hub_settings.save(ignore_permissions=True)
