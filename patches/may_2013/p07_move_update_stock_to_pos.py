# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, webnotes.defaults
from webnotes.utils import cint

def execute():
	webnotes.reload_doc("accounts", "doctype", "pos_setting")
	
	webnotes.conn.sql("""update `tabPOS Setting` set update_stock=%s""", 
		cint(webnotes.defaults.get_global_default("update_stock")))
	
	webnotes.conn.sql("""delete from `tabSingles`
		where doctype='Global Defaults' and field='update_stock'""")

	webnotes.conn.sql("""delete from `tabDefaultValue` 
		where parent='Control Panel' and defkey="update_stock" """)

	webnotes.defaults.clear_cache("Control Panel")

	webnotes.reload_doc("setup", "doctype", "global_defaults")
	
	# previously, update_stock was valid only when is_pos was checked
	# henceforth it is valid, and hence the patch
	webnotes.conn.sql("""update `tabSales Invoice` set update_stock=0 
		where ifnull(is_pos, 0)=0""")