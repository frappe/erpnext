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

def make_opportunity(access_token, args):
	buyer_name = "HUB-" + args["buyer_name"]
	email_id = args["email_id"]

	if not frappe.db.exists('Lead', {'email_id': email_id}):
		lead = frappe.new_doc("Lead")
		lead.lead_name = buyer_name
		lead.email_id = email_id
		lead.save(ignore_permissions=True)

	opportunity = frappe.new_doc("Opportunity")
	opportunity.enquiry_from = "Lead"
	opportunity.lead = frappe.get_all("Lead", filters={"email_id": email_id}, fields = ["name"])[0]["name"]
	opportunity.save(ignore_permissions=True)

	return 1

def disable_and_suspend_hub_user(access_token):
	hub_settings = get_hub_settings()
	hub_settings.publish = 0
	hub_settings.publish_pricing = 0
	hub_settings.publish_availability = 0
	hub_settings.suspended = 1
	hub_settings.enabled = 0
	hub_settings.save(ignore_permissions=True)
