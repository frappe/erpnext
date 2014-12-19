# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	for dt in ["workstation", "bom", "bom_operation"]:
		frappe.reload_doc("manufacturing", "doctype", dt)

	frappe.db.sql("update `tabWorkstation` set fixed_cost = fixed_cycle_cost, total_variable_cost = overhead")

	frappe.db.sql("update `tabBOM Operation` set fixed_cost = fixed_cycle_cost")

	for d in frappe.db.sql("select name from `tabBOM` where docstatus < 2"):
		try:
			bom = frappe.get_doc('BOM', d[0])
			if bom.docstatus == 1:
				bom.ignore_validate_update_after_submit = True
				bom.calculate_cost()
			bom.save()
		except:
			print "error", frappe.get_traceback()
			pass
