# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from erpnext.accounts.doctype.pricing_rule.utils import update_pricing_rule_table

def execute():
	frappe.reload_doc("accounts", "doctype", "pricing_rule_detail")

	doctypes = [
		'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice',
		'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Supplier Quotation'
	]

	for dt in doctypes:
		to_update = frappe.db.sql_list("""
			select p.name
			from `tab{0}` p
			where exists(select i.name from `tab{0} Item` i where i.parent = p.name and ifnull(i.pricing_rules, '') != '')
				and not exists(select r.name from `tabPricing Rule Detail` r where r.parenttype = '{0}' and r.parent = p.name)
				and p.docstatus < 2
		""".format(dt))

		for name in to_update:
			doc = frappe.get_doc(dt, name)
			update_pricing_rule_table(doc)

			for d in doc.pricing_rules:
				d.db_update()
