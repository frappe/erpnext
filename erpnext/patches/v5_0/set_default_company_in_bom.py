# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	for d in frappe.db.sql("""select name from `tabBOM` where docstatus < 2"""):
		try:
			bom = frappe.get_doc('BOM', d.name)
			bom.ignore_validate_update_after_submit = True
			bom.company = frappe.db.get_value("Global Defaults", None, "default_company")
			bom.save()
			frappe.db.commit()
		except:
			frappe.db.rollback()