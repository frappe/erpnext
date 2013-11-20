# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("utilities", "doctype", "address")

	webnotes.conn.sql("""update tabAddress set address_title = customer_name where ifnull(customer_name,'')!=''""")
	webnotes.conn.sql("""update tabAddress set address_title = supplier_name where ifnull(supplier_name,'')!=''""")
	webnotes.conn.sql("""update tabAddress set address_title = sales_partner where ifnull(sales_partner,'')!=''""")
	
	# move code to new doctype
	webnotes.conn.set_value("Website Script", None, "javascript", 
		webnotes.conn.get_value("Website Settings", None, "startup_code"))