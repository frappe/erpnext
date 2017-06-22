# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	""" delete deprecated reports """

	reports = ["Monthly Salary Register", "Customer Addresses And Contacts",
		"Supplier Addresses And Contacts"]

	for report in reports:
		if frappe.db.exists("Report", report):
			frappe.delete_doc("Report", report, ignore_permissions=True)