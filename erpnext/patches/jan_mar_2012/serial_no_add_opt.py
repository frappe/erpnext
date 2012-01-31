def execute():
	import webnotes
	opts = webnotes.conn.sql("""\
		SELECT options FROM `tabDocField`
		WHERE parent='Serial No' AND fieldname='status' AND
		fieldtype='Select'""")
	if opts and opts[0][0]:
		opt_list = opts[0][0].split("\n")
		if not "Purchase Returned" in opt_list:
			webnotes.conn.sql("""
				UPDATE `tabDocField` SET options=%s
				WHERE parent='Serial No' AND fieldname='status' AND
				fieldtype='Select'""", "\n".join(opt_list + ["Purchase Returned"]))
			webnotes.conn.commit()
			webnotes.conn.begin()

	from webnotes.modules.module_manager import reload_doc
	reload_doc('stock', 'doctype', 'serial_no')
