# Copyright (c) 2014, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "price_list")
	webnotes.conn.sql("""update `tabPrice List` set enabled=1""")