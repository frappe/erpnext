# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ("Material Request", "Purchase Order"):
		frappe.reload_doctype(doctype)
		frappe.reload_doctype(doctype + " Item")

		if not frappe.db.has_column(doctype, "schedule_date"):
			continue

		#Update only submitted MR
		for record in frappe.get_all(doctype, filters= [["docstatus", "=", 1]], fields=["name"]):
			doc = frappe.get_doc(doctype, record)
			if doc.items:
				if not doc.schedule_date:
					schedule_dates = [d.schedule_date for d in doc.items if d.schedule_date]
					if len(schedule_dates) > 0:
						min_schedule_date = min(schedule_dates)
						frappe.db.set_value(doctype, record,
							"schedule_date", min_schedule_date, update_modified=False)