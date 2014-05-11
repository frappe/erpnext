# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.reload_doc("stock", "doctype", "delivery_note")
	webnotes.conn.sql("""update `tabDelivery Note` set shipping_address_name = customer_address, 
		shipping_address = address_display""")