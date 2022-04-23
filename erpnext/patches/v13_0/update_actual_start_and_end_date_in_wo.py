
# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import add_to_date

def execute():
	frappe.reload_doc("manufacturing", "doctype", "work_order")
	frappe.reload_doc("manufacturing", "doctype", "work_order_item")
	frappe.reload_doc("manufacturing", "doctype", "job_card")

	data = frappe.get_all("Work Order",
		filters = {
			"docstatus": 1,
			"status": ("in", ["In Process", "Completed"])
		})

	for d in data:
		doc = frappe.get_doc("Work Order", d.name)
		doc.set_actual_dates()
		doc.db_set("actual_start_date", doc.actual_start_date, update_modified=False)

		if doc.status == "Completed":
			frappe.db.set_value("Work Order", d.name, {
				"actual_end_date": doc.actual_end_date,
				"lead_time": doc.lead_time
			}, update_modified=False)

			if not doc.planned_end_date:
				planned_end_date = add_to_date(doc.planned_start_date, minutes=doc.lead_time)
				doc.db_set("planned_end_date", doc.actual_start_date, update_modified=False)

	frappe.db.sql(""" UPDATE `tabJob Card` as jc, `tabWork Order` as wo
		SET
			jc.production_item = wo.production_item, jc.item_name = wo.item_name
		WHERE
			jc.work_order = wo.name and IFNULL(jc.production_item, "") = ""
	""")