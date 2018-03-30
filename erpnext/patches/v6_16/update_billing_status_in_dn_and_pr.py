# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for dt in ("Delivery Note", "Purchase Receipt"):
		frappe.reload_doctype(dt)
		frappe.reload_doctype(dt + " Item")

	# Update billed_amt in DN and PR which are not against any order
	for d in frappe.db.sql("""select name from `tabDelivery Note Item` item
		where (so_detail is null or so_detail = '') and docstatus=1""", as_dict=1):

		billed_amt = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
			where dn_detail=%s and docstatus=1""", d.name)
		billed_amt = billed_amt and billed_amt[0][0] or 0
		frappe.db.set_value("Delivery Note Item", d.name, "billed_amt", billed_amt, update_modified=False)

		frappe.db.commit()

	# Update billed_amt in DN and PR which are not against any order
	for d in frappe.db.sql("""select name from `tabPurchase Receipt Item` item
		where (purchase_order_item is null or purchase_order_item = '') and docstatus=1""", as_dict=1):

		billed_amt = frappe.db.sql("""select sum(amount) from `tabPurchase Invoice Item`
			where pr_detail=%s and docstatus=1""", d.name)
		billed_amt = billed_amt and billed_amt[0][0] or 0
		frappe.db.set_value("Purchase Receipt Item", d.name, "billed_amt", billed_amt, update_modified=False)

		frappe.db.commit()

	for dt in ("Delivery Note", "Purchase Receipt"):
		# Update billed amt which are against order or invoice
		# Update billing status for all
		for d in frappe.db.sql("select name from `tab{0}` where docstatus=1".format(dt), as_dict=1):
			doc = frappe.get_doc(dt, d.name)
			doc.update_billing_status(update_modified=False)
			doc.set_status(update=True, update_modified=False)

			frappe.db.commit()
