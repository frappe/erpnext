# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext

def execute():
	for company in frappe.get_all("Company"):
		if not erpnext.is_perpetual_inventory_enabled(company.name):
			continue

		acc_frozen_upto = frappe.db.get_value("Accounts Settings", None, "acc_frozen_upto") or "1900-01-01"
		pr_with_rejected_warehouse = frappe.db.sql("""
			select pr.name
			from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
			where pr.name = pr_item.parent
				and pr.posting_date > %s
				and pr.docstatus=1
				and pr.company = %s
				and pr_item.rejected_qty > 0
		""", (acc_frozen_upto, company.name), as_dict=1)

		for d in pr_with_rejected_warehouse:
			doc = frappe.get_doc("Purchase Receipt", d.name)

			doc.docstatus = 2
			doc.make_gl_entries_on_cancel()


			# update gl entries for submit state of PR
			doc.docstatus = 1
			doc.make_gl_entries()
