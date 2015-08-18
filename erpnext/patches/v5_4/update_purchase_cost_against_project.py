# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for p in frappe.get_all("Project"):
		project = frappe.get_doc("Project", p.name)
		project.update_purchase_costing()
		project.save()