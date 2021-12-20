import frappe


def execute():

	frappe.reload_doctype("Opportunity")
	if frappe.db.has_column("Opportunity", "enquiry_from"):
		frappe.db.sql(""" UPDATE `tabOpportunity` set opportunity_from = enquiry_from
			where coalesce(opportunity_from, '') = '' and coalesce(enquiry_from, '') != ''""")

	if frappe.db.has_column("Opportunity", "lead") and frappe.db.has_column("Opportunity", "enquiry_from"):
		frappe.db.sql(""" UPDATE `tabOpportunity` set party_name = lead
			where enquiry_from = 'Lead' and coalesce(party_name, '') = '' and coalesce(lead, '') != ''""")

	if frappe.db.has_column("Opportunity", "customer") and frappe.db.has_column("Opportunity", "enquiry_from"):
		frappe.db.sql(""" UPDATE `tabOpportunity` set party_name = customer
			 where enquiry_from = 'Customer' and coalesce(party_name, '') = '' and coalesce(customer, '') != ''""")
