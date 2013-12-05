# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("accounts", "doctype", "cost_center")
	webnotes.conn.sql("""update `tabCost Center` set company=company_name""")
	webnotes.conn.sql_ddl("""alter table `tabCost Center` drop column company_name""")