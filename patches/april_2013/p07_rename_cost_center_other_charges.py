# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("Accounts", "DocType", "Sales Taxes and Charges")
	webnotes.conn.sql("""update `tabSales Taxes and Charges`
		set cost_center = cost_center_other_charges""")
	webnotes.conn.sql_ddl("""alter table `tabSales Taxes and Charges`
		drop column cost_center_other_charges""")
	