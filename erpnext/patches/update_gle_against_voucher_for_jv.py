def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	
	# reload jv gl mapper
	reload_doc('accounts', 'GL Mapper', 'Journal Voucher')

	# select jv where against_jv exists
	jv = webnotes.conn.sql("select distinct parent from `tabJournal Voucher Detail` where docstatus = 1 and ifnull(against_jv, '') != ''")

	for d in jv:
		jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children=1)

		# cancel
		get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj = 1)

		#re-submit
		get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =0, adv_adj = 1)
