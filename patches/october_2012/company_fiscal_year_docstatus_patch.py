# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.sql("""update `tabCompany` set docstatus = 0
		where docstatus is null""")
		
	webnotes.conn.sql("""update `tabFiscal Year` set docstatus = 0
		where docstatus is null""")