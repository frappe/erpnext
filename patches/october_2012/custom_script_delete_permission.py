import webnotes
def execute():
	webnotes.conn.sql("""delete from `tabDocPerm` where parent='Custom Script'""")
	webnotes.conn.commit()
	
	from webnotes.model.sync import sync
	sync("core", "custom_script", force=1)
		
	webnotes.conn.begin()