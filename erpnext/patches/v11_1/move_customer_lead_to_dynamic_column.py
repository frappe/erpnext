# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doctype("Quotation")
	frappe.db.sql(""" UPDATE `tabQuotation` set party_name = lead WHERE quotation_to = 'Lead' """)
	frappe.db.sql(""" UPDATE `tabQuotation` set party_name = customer WHERE quotation_to = 'Customer' """)

	frappe.reload_doctype("Opportunity")
	frappe.db.sql(""" UPDATE `tabOpportunity` set party_name = lead WHERE opportunity_from = 'Lead' """)
	frappe.db.sql(
		""" UPDATE `tabOpportunity` set party_name = customer WHERE opportunity_from = 'Customer' """
	)
