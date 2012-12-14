def execute():
	import webnotes
	webnotes.conn.sql("""update `tabCustom Script` 
		set script = replace(script, 'createLocal', 'wn.model.make_new_doc_and_get_name') 
		where script_type='Client'""")