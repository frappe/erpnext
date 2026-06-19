# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.query_builder.functions import Lower
from frappe.rate_limiter import rate_limit
from frappe.utils import escape_html


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3 * 60)
def send_message(sender: str, message: str, subject: str = "Website Query"):
	from frappe.www.contact import send_message as website_send_message

	website_send_message(sender, message, subject)

	message = escape_html(message)

	oppotunity_creation = frappe.get_single_value(
		"CRM Settings", "enable_opportunity_creation_from_contact_us"
	)

	if not oppotunity_creation:
		# Meant to silently fail instead of throwing error.
		return

	lead = None
	customer = get_customer_from_contact_email(sender)

	if not customer:
		lead = frappe.db.get_value("Lead", dict(email_id=sender))
		if not lead:
			new_lead = frappe.get_doc(
				doctype="Lead", email_id=sender, lead_name=sender.split("@")[0].title()
			).insert(ignore_permissions=True)

	opportunity = frappe.get_doc(
		doctype="Opportunity",
		opportunity_from="Customer" if customer else "Lead",
		status="Open",
		title=subject,
		contact_email=sender,
	)

	if customer:
		opportunity.party_name = customer[0][0]
	elif lead:
		opportunity.party_name = lead
	else:
		opportunity.party_name = new_lead.name

	opportunity.insert(ignore_permissions=True)

	comm = frappe.get_doc(
		{
			"doctype": "Communication",
			"subject": subject,
			"content": message,
			"sender": sender,
			"sent_or_received": "Received",
			"reference_doctype": "Opportunity",
			"reference_name": opportunity.name,
		}
	)
	comm.insert(ignore_permissions=True)


def get_customer_from_contact_email(sender: str):
	dl = frappe.qb.DocType("Dynamic Link")
	contact = frappe.qb.DocType("Contact")
	return (
		frappe.qb.from_(dl)
		.left_join(contact)
		.on(dl.parent == contact.name)
		.select(dl.link_name)
		.distinct()
		.where((dl.link_doctype == "Customer") & (Lower(contact.email_id) == sender.lower()))
		.run()
	)
