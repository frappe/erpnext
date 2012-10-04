def execute():
	import webnotes
	webnotes.conn.sql("""delete from `tabSearch Criteria` \
		where name = 'customer_address_contact'""")
		
	from webnotes.modules import reload_doc
	reload_doc('report', 'customer_addresses_and_contacts', 'selling')