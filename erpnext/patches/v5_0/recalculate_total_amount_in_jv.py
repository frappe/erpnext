# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	for d in frappe.db.sql("""select name from `tabJournal Entry` where docstatus < 2 """, as_dict=1):
		try:
			jv = frappe.get_doc('Journal Entry', d.name)
			jv.ignore_validate_update_after_submit = True
			jv.set_print_format_fields()
			jv.save()
			frappe.db.commit()
		except:
			frappe.db.rollback()