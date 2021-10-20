import frappe
from erpnext.telephony.doctype.call_log.call_log import get_linked_call_logs

def update_lead_phone_numbers(contact, method):
	if contact.phone_nos:
		contact_lead = contact.get_link_for("Lead")
		if contact_lead:
			phone = mobile_no = contact.phone_nos[0].phone

			if len(contact.phone_nos) > 1:
				# get the default phone number
				primary_phones = [phone_doc.phone for phone_doc in contact.phone_nos if phone_doc.is_primary_phone]
				if primary_phones:
					phone = primary_phones[0]

				# get the default mobile number
				primary_mobile_nos = [phone_doc.phone for phone_doc in contact.phone_nos if phone_doc.is_primary_mobile_no]
				if primary_mobile_nos:
					mobile_no = primary_mobile_nos[0]

			lead = frappe.get_doc("Lead", contact_lead)
			lead.db_set("phone", phone)
			lead.db_set("mobile_no", mobile_no)

@frappe.whitelist()
def get_call_and_email_stats(doctype, docname):
	call_logs = frappe.db.sql('''SELECT
			COUNT(CASE WHEN cl.type = 'Incoming' THEN 1 END) AS incoming_calls,
			COUNT(CASE WHEN cl.type = 'Outgoing' THEN 1 END) AS outgoing_calls
		FROM `tabDynamic Link` dl INNER JOIN `tabCall Log` cl
		ON cl.name = dl.parent
		AND dl.parenttype = 'Call Log'
		AND dl.link_doctype='{0}' 
		AND dl.link_name ='{1}' '''.format(doctype, docname), as_dict=True)[0]
	
	email_stats = frappe.db.sql('''SELECT
			COUNT(CASE WHEN c.sent_or_received = 'Received' THEN 1 END) AS emails_received,
			COUNT(CASE WHEN c.sent_or_received = 'Sent' THEN 1 END) AS emails_sent
		FROM `tabCommunication` c
		WHERE c.reference_doctype='{0}' 
		AND c.reference_name ='{1}' '''.format(doctype, docname), as_dict=True)[0]

	return call_logs.update(email_stats)
