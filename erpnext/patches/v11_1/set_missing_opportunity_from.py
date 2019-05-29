from __future__ import unicode_literals
import frappe

def execute():

	frappe.reload_doctype("Opportunity")

	if frappe.db.exists("Opportunity", "enquiry_from"):
		frappe.db.sql(""" UPDATE `tabOpportunity` set opportunity_from = enquiry_from
			where opportunity_from IS NULL and enquiry_from IS NOT NULL""")

	if frappe.db.exists("Opportunity", "lead") and frappe.db.exists("Opportunity", "enquiry_from"):
		frappe.db.sql(""" UPDATE `tabOpportunity` set party_name = lead
			where enquiry_from = 'Lead' and party_name IS NULL and lead IS NOT NULL""")

	if frappe.db.exists("Opportunity", "customer") and frappe.db.exists("Opportunity", "enquiry_from"):
		frappe.db.sql(""" UPDATE `tabOpportunity` set party_name = customer
			 enquiry_from = 'Customer' and party_name IS NULL and customer IS NOT NULL""")