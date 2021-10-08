# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from six import iteritems


def execute():

	frappe.reload_doc('accounts', 'doctype', 'subscription')
	frappe.reload_doc('accounts', 'doctype', 'subscription_invoice')
	frappe.reload_doc('accounts', 'doctype', 'subscription_plan')

	if frappe.db.has_column('Subscription', 'customer'):
		frappe.db.sql("""
			UPDATE `tabSubscription`
			SET
				start_date = start,
				party_type = 'Customer',
				party = customer,
				sales_tax_template = tax_template
			WHERE IFNULL(party,'') = ''
		""")

	frappe.db.sql("""
		UPDATE `tabSubscription Invoice`
		SET document_type = 'Sales Invoice'
		WHERE IFNULL(document_type, '') = ''
	""")

	price_determination_map = {
		'Fixed rate': 'Fixed Rate',
		'Based on price list': 'Based On Price List'
	}

	for key, value in iteritems(price_determination_map):
		frappe.db.sql("""
			UPDATE `tabSubscription Plan`
			SET price_determination = %s
			WHERE price_determination = %s
		""", (value, key))
