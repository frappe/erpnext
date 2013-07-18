def execute():
	import webnotes
	webnotes.reload_doc("selling", "doctype", "selling_settings")
	ss = webnotes.bean("Selling Settings")
	
	same_rate = webnotes.conn.sql("""select field, value from `tabSingles` 
		where doctype = 'Global Defaults' and field = 'maintain_same_sales_rate'""")
	if same_rate:
		ss.doc.maintain_same_sales_rate = same_rate[1]
	else:
		ss.doc.maintain_same_sales_rate = 1
	
	ss.save()