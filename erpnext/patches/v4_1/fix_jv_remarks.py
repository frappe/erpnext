# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	reference_date = guess_reference_date()
	for name in frappe.db.sql_list("""select name from `tabJournal Voucher`
		where date(creation)>=%s""", reference_date):
		jv = frappe.get_doc("Journal Voucher", name)
		try:
			jv.create_remarks()
		except frappe.MandatoryError:
			pass
		else:
			frappe.db.set_value("Journal Voucher", jv.name, "remark", jv.remark)

def guess_reference_date():
	return (frappe.db.get_value("Patch Log", {"patch": "erpnext.patches.v4_0.validate_v3_patch"}, "creation")
		or "2014-05-06")
