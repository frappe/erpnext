# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	""" delete deprecated reports """

	reports = [
		"Monthly Salary Register", "Customer Addresses And Contacts",
		"Supplier Addresses And Contacts"
	]

	for report in reports:
		if frappe.db.exists("Report", report):
			check_and_update_desktop_icon_for_report(report)
			frappe.delete_doc("Report", report, ignore_permissions=True)

def check_and_update_desktop_icon_for_report(report):
	""" delete desktop icon for deprecated desktop icon and update the _report for Addresses And Contacts"""

	if report == "Monthly Salary Register":
		frappe.delete_doc("Desktop Icon", report)

	elif report in ["Customer Addresses And Contacts", "Supplier Addresses And Contacts"]:
		name = frappe.db.get_value("Desktop Icon", {"_report": report})
		if name:
			frappe.db.set_value("Desktop Icon", name, "_report", "Addresses And Contacts")

	frappe.db.commit()
