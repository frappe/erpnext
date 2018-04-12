# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CRMSettings(Document):
	pass

def make_popup(caller_no):
	contact_lookup = frappe.get_list("Contact", or_filters={"phone":caller_no, "mobile_no":caller_no}, ignore_permissions=True)

	if len(contact_lookup) > 0:
		contact_doc = frappe.get_doc("Contact", contact_lookup[0].get("name"))
		if(contact_doc.get_link_for('Customer')):
			customer_name = frappe.db.get_value("Dynamic Link", {"parent":contact_doc.get("name")}, "link_name")
			customer_full_name = frappe.db.get_value("Customer", customer_name, "customer_name")
			popup_data = {
				"title": "Customer",
				"number": caller_no,
				"name": customer_full_name,
				"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S')
			}

			popup_html = render_popup(popup_data)
			return popup_html

		elif(contact_doc.get_link_for('Lead')):
			lead_full_name = frappe.get_doc("Lead",contact_doc.get_link_for('Lead')).lead_name
			popup_data = {
				"title": "Lead",
				"number": caller_no,
				"name": lead_full_name,
				"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S')
			}
			popup_html = render_popup(popup_data)
			return popup_html

	else:
		popup_data = {
			"title": "Unknown Caller",
			"number": caller_no,
			"name": "Unknown",
			"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S')
		}
		popup_html = render_popup(popup_data)
		return popup_html

def render_popup(popup_data):
	html = frappe.render_template("frappe/public/js/integrations/call_popup.html", popup_data)
	return html

def display_popup(caller_no):
	# agent_no = popup_json.get("destination")

	try:
		popup_html = make_popup(caller_no)
		# if agent_id:
		# 	frappe.async.publish_realtime(event="msgprint", message=popup_html, user=agent_id)
		# else:
		users = frappe.get_all("Has Role", filters={"parenttype":"User","role":"Support Team"}, fields=["parent"])
		agents = [user.get("parent") for user in users]
		for agent in agents:
			frappe.async.publish_realtime(event="msgprint", message=popup_html, user=agent)

	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error in popup display")

@frappe.whitelist()
def get_caller_info(caller_no):
	if caller_no and len(caller_no) > 13:
		frappe.msgprint("Please enter a valid number")
		return

	contact_lookup = frappe.get_list("Contact", or_filters={"phone":caller_no, "mobile_no":caller_no}, ignore_permissions=True)

	if len(contact_lookup) > 0:
		contact_doc = frappe.get_doc("Contact", contact_lookup[0].get("name"))
		if(contact_doc.get_link_for('Customer')):
			customer_name = frappe.db.get_value("Dynamic Link", {"parent":contact_doc.get("name")}, "link_name")
			customer_full_name = frappe.db.get_value("Customer", customer_name, "customer_name")
			dashboard_data = {
				"title": "Customer",
				"number": caller_no,
				"name": customer_full_name,
				"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S')
			}

		elif(contact_doc.get_link_for('Lead')):
			lead_doc = frappe.get_doc("Lead",contact_doc.get_link_for('Lead'))
			dashboard_data = {
				"title": "Lead",
				"number": caller_no,
				"route_link":lead_doc.name,
				"name": lead_doc.lead_name or lead_doc.company_name,
				"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S')
			}

		open_issues = frappe.get_all("Issue", filters = {"contact":contact_doc.get("name")}, fields=["*"])
		dashboard_data["issue_list"] = open_issues
		return dashboard_data

	else:
		dashboard_data = {
			"title": "New Caller",
			"number": caller_no,
			"name": "Unknown",
			"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S'),
			"issue_list":[]
		}
		return dashboard_data