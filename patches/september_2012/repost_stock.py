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
def execute():
	import webnotes
	from stock.stock_ledger import update_entries_after
	res = webnotes.conn.sql("select distinct item_code, warehouse from `tabStock Ledger Entry`")
	i=0
	for d in res:
	    try:
			update_entries_after({ "item_code": d[0], "warehouse": d[1]})
	    except:
	        pass
	    i += 1
	    if i%100 == 0:
	        webnotes.conn.sql("commit")
	        webnotes.conn.sql("start transaction")