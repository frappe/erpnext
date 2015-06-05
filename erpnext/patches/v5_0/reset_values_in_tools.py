# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for dt in ["Payment Tool", "Bank Reconciliation", "Payment Reconciliation", "Leave Control Panel", 
		"Salary Manager", "Upload Attenadance", "Production Planning Tool", "BOM Replace Tool"]:
			frappe.db.sql("delete from `tabSingles` where doctype=%s", dt)
		