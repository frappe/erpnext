# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.sql("""update `tabDocType` set default_print_format=null
		where default_print_format='Standard'""")