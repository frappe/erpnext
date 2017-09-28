# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Purchase Order")
	frappe.reload_doctype("Purchase Order Item")

	if not frappe.db.has_column("Purchase Order", "schedule_date"):
		return

	#Update only submitted PO
	for po in frappe.get_all("Purchase Order", filters= [["docstatus", "=", 1]], fields=["name"]):
		purchase_order = frappe.get_doc("Purchase Order", po)
		if purchase_order.items:
			if not purchase_order.schedule_date:
				purchase_order.schedule_date = purchase_order.items[0].schedule_date
				purchase_order.save()