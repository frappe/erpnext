# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.manufacturing.doctype.work_order.work_order import create_job_card

def execute():
	frappe.reload_doc('manufacturing', 'doctype', 'work_order')
	frappe.reload_doc('manufacturing', 'doctype', 'work_order_item')
	frappe.reload_doc('manufacturing', 'doctype', 'job_card')
	frappe.reload_doc('manufacturing', 'doctype', 'job_card_item')

	fieldname = frappe.db.get_value('DocField', {'fieldname': 'work_order', 'parent': 'Timesheet'}, 'fieldname')
	if not fieldname:
		fieldname = frappe.db.get_value('DocField', {'fieldname': 'production_order', 'parent': 'Timesheet'}, 'fieldname')
		if not fieldname: return

	for d in frappe.get_all('Timesheet',
		filters={fieldname: ['!=', ""], 'docstatus': 0},
		fields=[fieldname, 'name']):
		if d[fieldname]:
			doc = frappe.get_doc('Work Order', d[fieldname])
			for row in doc.operations:
				create_job_card(doc, row, auto_create=True)
			frappe.delete_doc('Timesheet', d.name)
