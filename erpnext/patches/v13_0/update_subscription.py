# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():

	frappe.reload_doc('accounts', 'doctype', 'subscription')
	frappe.reload_doc('accounts', 'doctype', 'subscription_invoice')

	if frappe.db.has_column('Subscription', 'customer'):
		frappe.db.sql("""
			UPDATE `tabSubscription`
			SET party_type = 'Customer',
				party = customer,
				sales_tax_template = tax_template
			WHERE IFNULL(party,'') = ''
		""")

	frappe.db.sql("""
		UPDATE `tabSubscription Invoice`
		SET document_type = 'Sales Invoice'
		WHERE IFNULL(document_type, '') = ''
	""")