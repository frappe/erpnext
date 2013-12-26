# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.conn.sql("""delete from `tabDocPerm` where parent = 'BOM Replace Tool'""")
	webnotes.reload_doc("manufacturing", "doctype", "bom_replace_tool")