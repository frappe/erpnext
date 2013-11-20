# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.conn.sql("""update `tabStock Ledger Entry` set is_cancelled = 'No' 
		where ifnull(is_cancelled, '') = ''""")
		
	webnotes.conn.sql("""update tabBin b set b.stock_uom = 
		(select i.stock_uom from tabItem i where i.name = b.item_code) 
		where b.creation>='2013-09-01'""")