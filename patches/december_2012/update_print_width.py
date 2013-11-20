# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "docfield")
	webnotes.conn.sql("""update tabDocField set print_width = width""")