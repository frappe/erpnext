# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	webnotes.conn.sql("""update `tabStock Ledger Entry` sle, tabItem i 
		set sle.stock_uom = i.stock_uom 
		where sle.item_code = i.name and ifnull(sle.stock_uom, '') = ''""")