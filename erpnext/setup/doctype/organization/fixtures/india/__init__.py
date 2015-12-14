# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def install(company):
	docs = [
		{'doctype': 'Deduction Type', 'name': 'Professional Tax', 'description': 'Professional Tax', 'deduction_name': 'Professional Tax'},
		{'doctype': 'Deduction Type', 'name': 'Provident Fund', 'description': 'Provident fund', 'deduction_name': 'Provident Fund'},
		{'doctype': 'Earning Type', 'name': 'House Rent Allowance', 'description': 'House Rent Allowance', 'earning_name': 'House Rent Allowance', 'taxable': 'No'},
	]

	for d in docs:
		try:
			frappe.get_doc(d).insert()
		except frappe.NameError:
			pass
