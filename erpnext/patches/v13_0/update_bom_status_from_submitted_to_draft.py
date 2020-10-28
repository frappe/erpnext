# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	doctypes = ["BOM", "BOM Item", "BOM Explosion Item", "BOM Operation", "BOM Scrap Item"]

	for doctype in doctypes:
		frappe.reload_doc("manufacturing", "doctype", frappe.scrub(doctype))

	for doctype in doctypes:
		frappe.db.sql(""" UPDATE `tab{doc}`
			SET docstatus = 0 WHERE docstatus < 2
		""".format(doc=doctype))


	for row in frappe.get_all("Work Order", fields = ["name"],
		filters = {"docstatus": 1, "status": "In Process"}):
		work_order = frappe.get_doc("Work Order", row.name)
		work_order.update_work_order_qty()

		for d in work_order.required_items:
			d.db_update()