# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	reports_to_delete = ["Requested Items To Be Ordered",
		"Purchase Order Items To Be Received or Billed","Purchase Order Items To Be Received",
		"Purchase Order Items To Be Billed"]

	for report in reports_to_delete:
		if frappe.db.exists("Report", report):
			frappe.delete_doc("Report", report)