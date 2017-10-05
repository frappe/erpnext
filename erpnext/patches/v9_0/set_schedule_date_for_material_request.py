# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Material Request")
	frappe.reload_doctype("Material Request Item")

	if not frappe.db.has_column("Material Request", "schedule_date"):
		return

	#Update only submitted MR
	for mr in frappe.get_all("Material Request", filters= [["docstatus", "=", 1]], fields=["name"]):
		material_request = frappe.get_doc("Material Request", mr)
		if material_request.items:
			if not material_request.schedule_date:
				max_schedule_date = max([d.schedule_date for d in material_request.items])
				frappe.db.set_value("Material Request", mr,
					"schedule_date", max_schedule_date, update_modified=False)