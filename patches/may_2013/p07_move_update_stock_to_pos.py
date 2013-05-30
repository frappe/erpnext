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