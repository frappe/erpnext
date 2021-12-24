# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	frappe.reload_doc('setup', 'doctype', 'party_type')
	party_types = {'Customer': 'Receivable', 'Supplier': 'Payable',
		'Employee': 'Payable', 'Member': 'Receivable', 'Shareholder': 'Payable', 'Student': 'Receivable'}

	for party_type, account_type in party_types.items():
		frappe.db.set_value('Party Type', party_type, 'account_type', account_type)
