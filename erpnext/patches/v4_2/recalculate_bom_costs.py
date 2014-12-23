# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('manufacturing', 'doctype', 'bom_operation')
	for d in frappe.db.sql("""select bom.name from `tabBOM` bom where bom.docstatus < 2 and
		exists(select bom_op.name from `tabBOM Operation` bom_op where
		bom.name = bom_op.parent and bom_op.fixed_cycle_cost IS NOT NULL)""", as_dict=1):
		try:
			bom = frappe.get_doc('BOM', d.name)
			bom.ignore_validate_update_after_submit = True
			bom.calculate_cost()
			bom.save()
			frappe.db.commit()
		except:
			frappe.db.rollback()
