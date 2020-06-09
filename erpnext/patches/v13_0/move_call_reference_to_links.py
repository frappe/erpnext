import frappe

# move employee/lead/Contact to links
def execute():
	frappe.reload_doctype('Call Log')
	frappe.db.sql("UPDATE `tabCall Log` SET `type`='Incoming' where `type` is NULL")
	logs = frappe.get_all('Call Log', fields=['lead', 'contact', 'name', 'contact_name', 'lead_name'])
	for log in logs:
		links = []
		if log.lead:
			links.append({
				'link_doctype': 'Lead',
				'link_name': log.lead,
				'link_title': log.lead_name,
			})
		if log.contact:
			links.append({
				'link_doctype': 'Contact',
				'link_name': log.contact,
				'link_title': log.contact_name,
			})
		if links:
			call_log = frappe.get_doc('Call Log', log.name)
			call_log.set('links', links)
			call_log.save()
