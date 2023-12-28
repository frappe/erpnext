import frappe


def execute():
	frappe.reload_doc("crm", "doctype", "lead")
	frappe.db.sql(
		"""
		UPDATE "tabLead"
		SET title = CASE WHEN organization_lead = 1 THEN company_name ELSE lead_name END;
	"""
	)
