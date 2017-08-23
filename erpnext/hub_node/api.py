# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe, json
from frappe.utils import now, nowdate

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

	return "Success"