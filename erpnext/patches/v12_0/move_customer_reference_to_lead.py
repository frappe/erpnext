# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


def execute():
	frappe.reload_doc("crm", "doctype", "lead")
	frappe.reload_doc("selling", "doctype", "customer")

	customer_docs = frappe.get_all('Customer', filters={'lead_name': ['is', 'set']},
		fields=['name as customer', 'lead_name as lead'])

	for d in customer_docs:
		frappe.db.set_value('Lead', d.lead, 'customer', d.customer, update_modified=False)


