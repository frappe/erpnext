def execute():
	import webnotes
	import webnotes.modules
	res = webnotes.conn.sql("""\
		select module, name, standard from `tabPrint Format`
		where name like 'Sales Invoice%'""", as_dict=1)
	for r in res:
		if r.get('standard')=='Yes' and \
				r.get('name') in [
					'Sales Invoice Classic',
					'Sales Invoice Spartan',
					'Sales Invoice Modern'
				]:
			print r.get('name')
			webnotes.modules.reload_doc(r.get('module'), 'Print Format', r.get('name'))		
			