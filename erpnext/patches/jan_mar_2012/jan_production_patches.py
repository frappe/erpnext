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
	"""
		Patch includes:
		* Reload of Stock Entry Detail
	"""
	from webnotes.modules import reload_doc

	reload_doc('stock', 'doctype', 'stock_entry_detail')
	reload_doc('stock', 'doctype', 'item_supplier')
	reload_doc('stock', 'doctype', 'item')

	webnotes.conn.sql("""
		UPDATE tabDocField SET fieldtype='Float'
		WHERE parent='BOM'
		AND fieldname IN ('operating_cost', 'raw_material_cost', 'total_cost')
	""")

	webnotes.conn.sql("""
		UPDATE tabDocField SET fieldtype='Float'
		WHERE parent='BOM Item'
		AND fieldname IN ('qty', 'rate', 'amount', 'qty_consumed_per_unit')
	""")
	
	reload_doc('stock', 'doctype', 'stock_entry')
	reload_doc('production', 'doctype', 'bill_of_materials')
	reload_doc('production', 'doctype', 'bom_material')
