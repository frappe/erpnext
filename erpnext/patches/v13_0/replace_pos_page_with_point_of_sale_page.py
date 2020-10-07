from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists("Page", "point-of-sale"):
		frappe.rename_doc("Page", "pos", "point-of-sale", 1, 1)