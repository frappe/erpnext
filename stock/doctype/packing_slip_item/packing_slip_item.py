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

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_item_details(self, delivery_note):
		res = webnotes.conn.sql("""\
			SELECT item_name, SUM(IFNULL(qty, 0)) as total_qty,
			IFNULL(packed_qty,	0) as packed_qty, stock_uom
			FROM `tabDelivery Note Item`
			WHERE parent=%s AND item_code=%s GROUP BY item_code""",
			(delivery_note, self.doc.item_code), as_dict=1)

		if res and len(res)>0:
			res = res[0]
			res['qty'] = res['total_qty'] - res['packed_qty']
			res['qty'] = self.doc.qty or (res['qty']>=0 and res['qty'] or 0)
			del res['total_qty']
			del res['packed_qty']
			self.doc.fields.update(res)

		res = webnotes.conn.sql("""\
			SELECT net_weight, weight_uom FROM `tabItem`
			WHERE name=%s""", self.doc.item_code, as_dict=1)

		if res and len(res)>0:
			res = res[0]
			self.doc.fields.update(res)
