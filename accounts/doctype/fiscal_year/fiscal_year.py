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

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def set_as_default(self):
		webnotes.conn.set_value("Global Defaults", None, "current_fiscal_year", self.doc.name)
		webnotes.get_obj("Global Defaults").on_update()
		
		# clear cache
		webnotes.clear_cache()
		
		msgprint(self.doc.name + _(""" is now the default Fiscal Year. \
			Please refresh your browser for the change to take effect."""))

test_records = [
	[{
		"doctype": "Fiscal Year", 
		"year": "_Test Fiscal Year 2013", 
		"year_start_date": "2013-01-01"
	}],
	[{
		"doctype": "Fiscal Year",
		"year": "_Test Fiscal Year 2014", 
		"year_start_date": "2014-01-01"
	}]
]