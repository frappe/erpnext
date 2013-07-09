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

def execute():
	updated_bom = []
	for bom in webnotes.conn.sql("select name from tabBOM where docstatus < 2"):
		if bom[0] not in updated_bom:
			try:
				bom_obj = webnotes.get_obj("BOM", bom[0], with_children=1)
				updated_bom += bom_obj.update_cost_and_exploded_items(bom[0])
				webnotes.conn.commit()
			except:
				pass