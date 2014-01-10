# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

def execute():
	webnotes.reload_doc("stock", "doctype", "price_list")
	webnotes.reload_doc("stock", "doctype", "item_price")

	webnotes.conn.sql("""update `tabPrice List` pl, `tabItem Price` ip 
		set pl.selling=ip.selling, pl.buying=ip.buying 
		where pl.name=ip.price_list_name""")