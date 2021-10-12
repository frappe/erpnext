# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from erpnext.accounts.utils import check_and_delete_linked_reports


def execute():
	reports_to_delete = ["Ordered Items To Be Delivered", "Ordered Items To Be Billed"]

	for report in reports_to_delete:
		if frappe.db.exists("Report", report):
			delete_auto_email_reports(report)
			check_and_delete_linked_reports(report)

			frappe.delete_doc("Report", report)

def delete_auto_email_reports(report):
	""" Check for one or multiple Auto Email Reports and delete """
	auto_email_reports = frappe.db.get_values("Auto Email Report", {"report": report}, ["name"])
	for auto_email_report in auto_email_reports:
		frappe.delete_doc("Auto Email Report", auto_email_report[0])
