# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("manufacturing", "doctype", "job_card")
	frappe.reload_doc("manufacturing", "doctype", "job_card_item")
	frappe.reload_doc("manufacturing", "doctype", "work_order_operation")

	frappe.db.sql(""" update `tabJob Card` jc, `tabWork Order Operation` wo
		SET	jc.hour_rate =  wo.hour_rate
		WHERE
			jc.operation_id = wo.name and jc.docstatus < 2 and wo.hour_rate > 0
	""")