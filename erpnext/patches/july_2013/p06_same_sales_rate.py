# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.reload_doc("selling", "doctype", "selling_settings")
	ss = webnotes.bean("Selling Settings")
	
	same_rate = webnotes.conn.get_value("Global Defaults", "maintain_same_sales_rate")

	if same_rate or same_rate == 0:
		ss.doc.maintain_same_sales_rate = same_rate
	else:
		ss.doc.maintain_same_sales_rate = 1

	ss.save()