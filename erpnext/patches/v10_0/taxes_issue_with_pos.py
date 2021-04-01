# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for d in frappe.get_all('Sales Invoice', fields=["name"],
		filters = {'is_pos':1, 'docstatus': 1, 'creation': ('>', '2018-04-23')}):
		doc = frappe.get_doc('Sales Invoice', d.name)
		if (not doc.taxes and doc.taxes_and_charges and doc.pos_profile and doc.outstanding_amount != 0 and
			frappe.db.get_value('POS Profile', doc.pos_profile, 'taxes_and_charges', cache=True) == doc.taxes_and_charges):

			doc.append_taxes_from_master()
			doc.calculate_taxes_and_totals()
			for d in doc.taxes:
				d.db_update()

			doc.db_update()

			delete_gle_for_voucher(doc.name)
			doc.make_gl_entries()

def delete_gle_for_voucher(voucher_no):
	frappe.db.sql("""delete from `tabGL Entry` where voucher_no = %(voucher_no)s""",
		{'voucher_no': voucher_no})