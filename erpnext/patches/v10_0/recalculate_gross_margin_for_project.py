# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('projects', 'doctype', 'project')
	for d in frappe.db.sql(""" select name from `tabProject` where
		ifnull(total_consumed_material_cost, 0 ) > 0 and ifnull(total_billed_amount, 0) > 0""", as_dict=1):
		doc = frappe.get_doc("Project", d.name)
		doc.calculate_gross_margin()
		doc.db_set('gross_margin', doc.gross_margin)
		doc.db_set('per_gross_margin', doc.per_gross_margin)