# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import comma_or, cint
from webnotes.model.controller import DocListController
import webnotes.defaults

class DocType(DocListController):
	def onload(self):
		self.doclist.extend(webnotes.conn.sql("""select * from `tabItem Price` 
			where price_list_name=%s""", self.doc.name, as_dict=True, update={"doctype": "Item Price"}))
	
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
		
	def on_update(self):
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		if cint(cart_settings.doc.enabled):
			cart_settings.validate_price_lists()
				
	def on_trash(self):
		webnotes.conn.sql("""delete from `tabItem Price` where price_list_name = %s""", 
			self.doc.name)