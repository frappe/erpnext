# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.conn.sql("""update `tabItem Price` ip INNER JOIN `tabItem` i 
		ON (ip.item_code = i.name) 
		set ip.item_name = i.item_name, ip.item_description = i.description""")