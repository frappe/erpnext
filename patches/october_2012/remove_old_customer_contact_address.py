def execute():
	import webnotes
	webnotes.conn.sql("""delete from `tabSearch Criteria` \
		where name = 'customer_address_contact'""")
	
	webnotes.reload_doc("core", "doctype", "docfield")
	webnotes.reload_doc("core", "doctype", "report")
	webnotes.reload_doc('selling', 'report', 'customer_addresses_and_contacts')