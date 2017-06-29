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
			check_and_update_auto_email_report(report)
			frappe.db.commit()

			frappe.delete_doc("Report", report, ignore_permissions=True)

def check_and_update_desktop_icon_for_report(report):
	""" delete or update desktop icon"""
	desktop_icons = frappe.db.sql_list("""select name from `tabDesktop Icon`
		where _report='{0}'""".format(report))

	if not desktop_icons:
		return

	if report == "Monthly Salary Register":
		for icon in desktop_icons:
			frappe.delete_doc("Desktop Icon", icon)

	elif report in ["Customer Addresses And Contacts", "Supplier Addresses And Contacts"]:
		frappe.db.sql("""update `tabDesktop Icon` set _report='{value}'
			where name in ({docnames})""".format(
				value="Addresses And Contacts",
				docnames=",".join(["'%s'"%icon for icon in desktop_icons])
			)
		)

def check_and_update_auto_email_report(report):
	""" delete or update auto email report for deprecated report """

	auto_email_report = frappe.db.get_value("Auto Email Report", {"report": report})
	if not auto_email_report:
		return

	if report == "Monthly Salary Register":
		frappe.delete_doc("Auto Email Report", auto_email_report)

	elif report in ["Customer Addresses And Contacts", "Supplier Addresses And Contacts"]:
		frapppe.db.set_value("Auto Email Report", auto_email_report, "report", report)