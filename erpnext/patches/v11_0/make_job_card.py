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

	for d in frappe.db.sql("""select work_order, name from tabTimesheet
		where (work_order is not null and work_order != '') and docstatus = 0""", as_dict=1):
		if d.work_order:
			doc = frappe.get_doc('Work Order', d.work_order)
			for row in doc.operations:
				create_job_card(doc, row, auto_create=True)
			frappe.delete_doc('Timesheet', d.name)