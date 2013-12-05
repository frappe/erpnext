# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.clear_perms("Employee")
	webnotes.reload_doc("hr", "doctype", "employee")
	webnotes.conn.sql("""update tabEmployee set employee=name""")
