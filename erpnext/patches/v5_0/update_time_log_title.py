# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Time Log")
	for d in frappe.get_all("Time Log"):
		time_log = frappe.get_doc("Time Log", d.name)
		time_log.set_title()
		frappe.db.set_value("Time Log", time_log.name, "title", time_log.title)
