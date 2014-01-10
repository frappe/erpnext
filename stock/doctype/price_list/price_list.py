# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _, throw
from webnotes.utils import cint
from webnotes.model.controller import DocListController
import webnotes.defaults

class DocType(DocListController):
	def validate(self):
		if not cint(self.doc.buying) and not cint(self.doc.selling):
			throw(_("Price List must be applicable for Buying or Selling"))
				
		if not self.doclist.get({"parentfield": "valid_for_territories"}):
			# if no territory, set default territory
			if webnotes.defaults.get_user_default("territory"):
				self.doclist.append({
					"doctype": "Applicable Territory",
					"parentfield": "valid_for_territories",
					"territory": webnotes.defaults.get_user_default("territory")
				})
			else:
				# at least one territory
				self.validate_table_has_rows("valid_for_territories")

	def on_update(self):
		self.set_default_if_missing()
		self.update_item_price()
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		if cint(cart_settings.doc.enabled):
			cart_settings.validate_price_lists()

	def set_default_if_missing(self):
		if cint(self.doc.selling):
			if not webnotes.conn.get_value("Selling Settings", None, "selling_price_list"):
				webnotes.set_value("Selling Settings", "Selling Settings", "selling_price_list", self.doc.name)

		elif cint(self.doc.buying):
			if not webnotes.conn.get_value("Buying Settings", None, "buying_price_list"):
				webnotes.set_value("Buying Settings", "Buying Settings", "buying_price_list", self.doc.name)

	def update_item_price(self):
		webnotes.conn.sql("""update `tabItem Price` set currency=%s, 
			buying=%s, selling=%s, modified=NOW() where price_list=%s""", 
			(self.doc.currency, cint(self.doc.buying), cint(self.doc.selling), self.doc.name))