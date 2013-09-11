# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import comma_or, cint
from webnotes.model.controller import DocListController
import webnotes.defaults

class PriceListDuplicateItem(Exception): pass

class DocType(DocListController):
	def validate(self):
		if self.doc.buying_or_selling not in ["Buying", "Selling"]:
			msgprint(_(self.meta.get_label("buying_or_selling")) + " " + _("must be one of") + " " +
				comma_or(["Buying", "Selling"]), raise_exception=True)
				
		if not self.doclist.get({"parentfield": "valid_for_territories"}):
			# if no territory, set default territory
			if webnotes.defaults.get_user_default("territory"):
				self.doclist.append({
					"doctype": "For Territory",
					"parentfield": "valid_for_territories",
					"territory": webnotes.defaults.get_user_default("territory")
				})
			else:
				# at least one territory
				self.validate_table_has_rows("valid_for_territories")

		# check for duplicate items
		self.check_duplicate_items()
		
	def on_update(self):
		self.set_default_if_missing()
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		if cint(cart_settings.doc.enabled):
			cart_settings.validate_price_lists()

	def check_duplicate_items(self):
		item_codes = []
		for d in self.doclist.get({"parentfield": "item_prices"}):
			if d.item_code not in item_codes:
				item_codes.append(d.item_code)
			else:
				msgprint(_("Duplicate Item ") + ": " + d.item_code, raise_exception=PriceListDuplicateItem)
				
	def set_default_if_missing(self):
		if self.doc.buying_or_selling=="Selling":
			if not webnotes.conn.get_value("Selling Settings", None, "selling_price_list"):
				webnotes.set_value("Selling Settings", "Selling Settings", "selling_price_list", self.doc.name)

		elif self.doc.buying_or_selling=="Buying":
			if not webnotes.conn.get_value("Buying Settings", None, "buying_price_list"):
				webnotes.set_value("Buying Settings", "Buying Settings", "buying_price_list", self.doc.name)

