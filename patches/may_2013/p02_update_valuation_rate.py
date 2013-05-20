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
	from stock.stock_ledger import update_entries_after
	item_warehouse = []
	# update valuation_rate in transaction
	doctypes = {"Purchase Receipt": "purchase_receipt_details", "Purchase Invoice": "entries"}
	
	for dt in doctypes:
		for d in webnotes.conn.sql("""select name from `tab%s` 
				where modified >= '2013-05-09' and docstatus=1""" % dt):
			rec = webnotes.get_obj(dt, d[0])
			rec.update_valuation_rate(doctypes[dt])
			
			for item in rec.doclist.get({"parentfield": doctypes[dt]}):
				webnotes.conn.sql("""update `tab%s Item` set valuation_rate = %s 
					where name = %s"""% (dt, '%s', '%s'), tuple([item.valuation_rate, item.name]))
					
				if dt == "Purchase Receipt":
					webnotes.conn.sql("""update `tabStock Ledger Entry` set incoming_rate = %s 
						where voucher_detail_no = %s""", (item.valuation_rate, item.name))
					if [item.item_code, item.warehouse] not in item_warehouse:
						item_warehouse.append([item.item_code, item.warehouse])
			
	for d in item_warehouse:
		try:
			update_entries_after({"item_code": d[0], "warehouse": d[1], 
				"posting_date": "2013-01-01", "posting_time": "00:05:00"})
			webnotes.conn.commit()
		except:
			pass