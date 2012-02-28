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

import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def on_update(self):
		tmp = None
		for d in self.doclist:
			if d.doctype=="Product Group":
				import json
				tmp = json.dumps({"item_group": d.item_group, "label":d.label})
				break
				
		webnotes.conn.set_default("default_product_category", tmp)
		
		from webnotes.session_cache import clear_cache
		clear_cache('Guest')