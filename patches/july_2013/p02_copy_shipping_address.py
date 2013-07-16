def execute():
	import webnotes
	webnotes.reload_doc("stock", "doctype", "delivery_note")
	webnotes.conn.sql("""update `tabDelivery Note` set shipping_address_name = customer_address, 
		shipping_address = address_display""")