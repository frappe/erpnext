# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	from webnotes.utils import cint
	webnotes.reload_doc("setup", "doctype", "global_defaults")
	
	doctype_list = webnotes.get_doctype("Sales Invoice")
	update_stock_df = doctype_list.get_field("update_stock")
	
	global_defaults = webnotes.bean("Global Defaults", "Global Defaults")
	global_defaults.doc.update_stock = cint(update_stock_df.default)
	global_defaults.save()

	webnotes.conn.sql("""delete from `tabProperty Setter`
		where doc_type='Sales Invoice' and doctype_or_field='DocField'
		and field_name='update_stock' and property='default'""")
		
	webnotes.reload_doc("accounts", "doctype", "sales_invoice")