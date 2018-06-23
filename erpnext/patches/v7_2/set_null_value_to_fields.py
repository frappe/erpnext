# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	fields = {"Cost Center": "project", "Project": "cost_center"}
	for budget_against, field in fields.items():
		frappe.db.sql(""" update `tabBudget` set {field} = null
			where budget_against = %s """.format(field = field), budget_against)
