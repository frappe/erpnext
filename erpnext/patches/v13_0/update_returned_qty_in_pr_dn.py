# Copyright (c) 2021, Frappe and Contributors
# License: GNU General Public License v3. See license.txt
import frappe

from erpnext.controllers.status_updater import OverAllowanceError


def execute():
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt_item')
	frappe.reload_doc('stock', 'doctype', 'delivery_note')
	frappe.reload_doc('stock', 'doctype', 'delivery_note_item')
	frappe.reload_doc('stock', 'doctype', 'stock_settings')

	def update_from_return_docs(doctype):
		for return_doc in frappe.get_all(doctype, filters={'is_return' : 1, 'docstatus' : 1, 'return_against': ('!=', '')}):
			# Update original receipt/delivery document from return
			return_doc = frappe.get_cached_doc(doctype, return_doc.name)
			try:
				return_doc.update_prevdoc_status()
			except OverAllowanceError:
				frappe.db.rollback()
				continue

			return_against = frappe.get_doc(doctype, return_doc.return_against)
			return_against.update_billing_status()
			frappe.db.commit()

	# Set received qty in stock uom in PR, as returned qty is checked against it
	frappe.db.sql(""" update `tabPurchase Receipt Item`
		set received_stock_qty = received_qty * conversion_factor
		where docstatus = 1 """)

	for doctype in ('Purchase Receipt', 'Delivery Note'):
		update_from_return_docs(doctype)
