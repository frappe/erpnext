import frappe

def execute():
	domains = ['Education', 'Healthcare', 'Hospitality']
	try:
		for d in domains:
			domain = frappe.get_doc('Domain', d)
			domain.setup_domain()
	except frappe.LinkValidationError:
		pass
