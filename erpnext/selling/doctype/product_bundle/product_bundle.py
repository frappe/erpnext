# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import get_link_to_form

from frappe import _

from frappe.model.document import Document

class ProductBundle(Document):
	def autoname(self):
		self.name = self.new_item_code

	def validate(self):
		self.validate_main_item()
		self.validate_child_items()
		from erpnext.utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self, "uom", "qty")

	def on_trash(self):
		linked_doctypes = ["Delivery Note", "Sales Invoice", "POS Invoice", "Purchase Receipt", "Purchase Invoice",
			"Stock Entry", "Stock Reconciliation", "Sales Order", "Purchase Order", "Material Request"]

		invoice_links = []
		for doctype in linked_doctypes:
			item_doctype = doctype + " Item"

			if doctype == "Stock Entry":
				item_doctype = doctype + " Detail"

			invoices = frappe.db.get_all(item_doctype, {"item_code": self.new_item_code, "docstatus": 1}, ["parent"])

			for invoice in invoices:
				invoice_links.append(get_link_to_form(doctype, invoice['parent']))

		if len(invoice_links):
			frappe.throw(
				"This Product Bundle is linked with {0}. You will have to cancel these documents in order to delete this Product Bundle"
				.format(", ".join(invoice_links)), title=_("Not Allowed"))

	def validate_main_item(self):
		"""Validates, main Item is not a stock item"""
		if frappe.db.get_value("Item", self.new_item_code, "is_stock_item"):
			frappe.throw(_("Parent Item {0} must not be a Stock Item").format(self.new_item_code))

	def validate_child_items(self):
		for item in self.items:
			if frappe.db.exists("Product Bundle", item.item_code):
				frappe.throw(_("Row #{0}: Child Item should not be a Product Bundle. Please remove Item {1} and Save").format(item.idx, frappe.bold(item.item_code)))

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_new_item_code(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	return frappe.db.sql("""select name, item_name, description from tabItem
		where is_stock_item=0 and name not in (select name from `tabProduct Bundle`)
		and %s like %s %s limit %s, %s""" % (searchfield, "%s",
		get_match_cond(doctype),"%s", "%s"),
		("%%%s%%" % txt, start, page_len))
