# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	pro_orders = webnotes.conn.sql("""select name from `tabProduction Order`
		where docstatus=1 and status!='Stopped'""")

	for p in pro_orders:
		webnotes.bean("Production Order", p[0]).run_method("update_status")
