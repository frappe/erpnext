# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "pos_payment_method")
	pos_profiles = frappe.get_all("POS Profile")

	for pos_profile in pos_profiles:
		payments = frappe.db.sql("""
			select idx, parentfield, parenttype, parent, mode_of_payment, `default` from `tabSales Invoice Payment` where parent=%s
		""", pos_profile.name, as_dict=1)
		if payments:
			for payment_mode in payments:
				pos_payment_method = frappe.new_doc("POS Payment Method")
				pos_payment_method.idx = payment_mode.idx
				pos_payment_method.default = payment_mode.default
				pos_payment_method.mode_of_payment = payment_mode.mode_of_payment
				pos_payment_method.parent = payment_mode.parent
				pos_payment_method.parentfield = payment_mode.parentfield
				pos_payment_method.parenttype = payment_mode.parenttype
				pos_payment_method.db_insert()
		
		frappe.db.sql("""delete from `tabSales Invoice Payment` where parent=%s""", pos_profile.name)
