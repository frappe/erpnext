# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt

def execute():
	frappe.reload_doctype("Sales Invoice")
	frappe.reload_doctype("Sales Invoice Item")
	
	for si in frappe.get_all("Sales Invoice", fields = ["name"], 
		filters={"docstatus": 1, "is_pos": 1, "is_return": 1}):
		si_doc = frappe.get_doc("Sales Invoice", si.name)
		if len(si_doc.payments) > 0:
			si_doc.set_paid_amount()
			si_doc.flags.ignore_validate_update_after_submit = True
			si_doc.save()
			if si_doc.grand_total <= si_doc.paid_amount and si_doc.paid_amount < 0:
				delete_gle_for_voucher(si_doc.name)
				si_doc.run_method("make_gl_entries")

def delete_gle_for_voucher(voucher_no):
	frappe.db.sql("""delete from `tabGL Entry` where voucher_no = %(voucher_no)s""",
		{'voucher_no': voucher_no})
