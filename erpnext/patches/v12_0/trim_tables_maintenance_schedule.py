# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.meta import trim_tables


def execute():
	frappe.reload_doc("maintenance", "doctype", "maintenance_schedule")
	frappe.reload_doc("maintenance", "doctype", "maintenance_schedule_detail")

	trim_tables('Maintenance Schedule')
	trim_tables('Maintenance Schedule Detail')
