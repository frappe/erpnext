import frappe


def execute():
	lead = frappe.qb.DocType("Lead")
	frappe.qb.update(lead).set(lead.disabled, 0).set(lead.docstatus, 0).where(
		lead.disabled == 1 and lead.docstatus == 1
	).run()
