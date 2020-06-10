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
			check_and_update_auto_email_report(report)
			frappe.db.commit()

			frappe.delete_doc("Report", report, ignore_permissions=True)

def check_and_update_auto_email_report(report):
	""" delete or update auto email report for deprecated report """

	auto_email_report = frappe.db.get_value("Auto Email Report", {"report": report})
	if not auto_email_report:
		return

	if report == "Monthly Salary Register":
		frappe.delete_doc("Auto Email Report", auto_email_report)

	elif report in ["Customer Addresses And Contacts", "Supplier Addresses And Contacts"]:
		frappe.db.set_value("Auto Email Report", auto_email_report, "report", report)