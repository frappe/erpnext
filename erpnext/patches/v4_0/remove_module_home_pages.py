# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for page in ("accounts-home", "website-home", "support-home", "stock-home", "selling-home", "projects-home",
		"manufacturing-home", "hr-home", "buying-home"):
		frappe.delete_doc("Page", page)