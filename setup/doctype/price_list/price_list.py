# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import comma_or, cint
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def onload(self):
		self.doclist.extend(webnotes.conn.sql("""select * from `tabItem Price` 
			where price_list_name=%s""", self.doc.name, as_dict=True, update={"doctype": "Item Price"}))
	
	def validate(self):
		if self.doc.buying_or_selling not in ["Buying", "Selling"]:
			msgprint(_(self.meta.get_label("buying_or_selling")) + " " + _("must be one of") + " " +
				comma_or(["Buying", "Selling"]), raise_exception=True)
				
		# at least one territory
		self.validate_table_has_rows("valid_for_territories")
		
	def on_update(self):
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		if cint(cart_settings.doc.enabled):
			cart_settings.validate_price_lists()
				
	def on_trash(self):
		webnotes.conn.sql("""delete from `tabItem Price` where price_list_name = %s""", 
			self.doc.name)