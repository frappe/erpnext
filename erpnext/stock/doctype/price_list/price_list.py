# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _, throw
from frappe.utils import cint
from frappe.model.controller import DocListController
import frappe.defaults

class DocType(DocListController):
	def validate(self):
		if not cint(self.doc.buying) and not cint(self.doc.selling):
			throw(_("Price List must be applicable for Buying or Selling"))
				
		if not self.doclist.get({"parentfield": "valid_for_territories"}):
			# if no territory, set default territory
			if frappe.defaults.get_user_default("territory"):
				self.doclist.append({
					"doctype": "Applicable Territory",
					"parentfield": "valid_for_territories",
					"territory": frappe.defaults.get_user_default("territory")
				})
			else:
				# at least one territory
				self.validate_table_has_rows("valid_for_territories")

	def on_update(self):
		self.set_default_if_missing()
		self.update_item_price()

	def set_default_if_missing(self):
		if cint(self.doc.selling):
			if not frappe.conn.get_value("Selling Settings", None, "selling_price_list"):
				frappe.set_value("Selling Settings", "Selling Settings", "selling_price_list", self.doc.name)

		elif cint(self.doc.buying):
			if not frappe.conn.get_value("Buying Settings", None, "buying_price_list"):
				frappe.set_value("Buying Settings", "Buying Settings", "buying_price_list", self.doc.name)

	def update_item_price(self):
		frappe.conn.sql("""update `tabItem Price` set currency=%s, 
			buying=%s, selling=%s, modified=NOW() where price_list=%s""", 
			(self.doc.currency, cint(self.doc.buying), cint(self.doc.selling), self.doc.name))
