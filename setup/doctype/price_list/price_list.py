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
from webnotes.utils import cint


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def onload(self):
		self.doclist.extend(webnotes.conn.sql("""select * from `tabItem Price` 
			where price_list_name=%s""", self.doc.name, as_dict=True, update={"doctype": "Item Price"}))
	
	def validate(self):
		if not (cint(self.doc.valid_for_all_countries) or len(self.doclist.get({"parentfield": "valid_for_countries"}))):
			msgprint(_("""Please check "Valid For All Countries" or \
				enter atlease one row in the "Countries" table."""), raise_exception=True)
	
