import frappe


def execute():
	frappe.reload_doc("crm", "doctype", "lead")
	for lead in frappe.get_all("Lead", fields=["name", "organization_lead", "company_name", "lead_name"]):
		frappe.db.set_value(
			"Lead",
			lead.name,
			"title",
			lead.company_name if lead.organization_lead else lead.lead_name,
			update_modified=False,
		)
