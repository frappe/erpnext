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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def get_rate(self, arg):
		from webnotes.model.code import get_obj
		return get_obj('Sales Common').get_rate(arg)
		
	def validate(self):
		if self.doc.is_default == 1:
			webnotes.conn.sql("""update `tabSales Taxes and Charges Master` set is_default = 0 
				where ifnull(is_default,0) = 1 and name != %s and company = %s""", 
				(self.doc.name, self.doc.company))
				
		# at least one territory
		self.validate_table_has_rows("valid_for_territories")
		
	def on_update(self):
		cart_settings = webnotes.get_obj("Shopping Cart Settings")
		if cint(cart_settings.doc.enabled):
			cart_settings.validate_tax_masters()