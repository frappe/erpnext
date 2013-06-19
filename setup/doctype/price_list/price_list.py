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
from webnotes.utils import cint, comma_or
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def onload(self):
		self.doclist.extend(webnotes.conn.sql("""select * from `tabItem Price` 
			where price_list_name=%s""", self.doc.name, as_dict=True, update={"doctype": "Item Price"}))
	
	def validate(self):
		if not (cint(self.doc.valid_for_all_countries) or len(self.doclist.get({"parentfield": "valid_for_countries"}))):
			msgprint(_("""Please check "Valid For All Countries" or \
				enter atlease one row in the "Countries" table."""), raise_exception=True)
				
		if self.doc.buying_or_selling not in ["Buying", "Selling"]:
			msgprint(_(self.meta.get_label("buying_or_selling")) + " " + _("must be one of") + " " +
				comma_or(["Buying", "Selling"]), raise_exception=True)
				
		self.validate_use_for_website()
		
	def validate_use_for_website(self):
		if self.doc.use_for_website:
			if self.doc.valid_for_all_countries:
				if webnotes.conn.sql("""select name from `tabPrice List` where use_for_website=1
					and valid_for_all_countries=1 and name!=%s""", self.doc.name):
						webnotes.msgprint(_("Error: Another Price List already exists that is used for website and is valid for all countries."), 
							raise_exception=True)
				
			elif self.doclist.get({"parentfield": "valid_for_countries"}):
				for d in self.doclist.get({"parentfield": "valid_for_countries"}):
					if webnotes.conn.sql("""select country from `tabPrice List Country` plc, `tabPrice List` pl
						where plc.parent=pl.name and pl.use_for_website=1 and 
						ifnull(valid_for_all_countries, 0)=0 and country=%s and pl.name!=%s""", 
						(d.country, self.doc.name)):
							webnotes.msgprint(_("Error: Another Price List already exists that is used for website and is valid for country") 
								+ ": " + d.country, raise_exception=True)
	
	def on_trash(self):
		webnotes.conn.sql("""delete from `tabItem Price` where price_list_name = %s""", 
			self.doc.name)