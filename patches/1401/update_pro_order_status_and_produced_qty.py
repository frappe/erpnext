# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	from manufacturing.doctype.production_order.production_order import StockOverProductionError
	pro_orders = webnotes.conn.sql("""select name from `tabProduction Order`
		where docstatus=1 and status!='Stopped'""")

	for p in pro_orders:
		try:
			production_order = webnotes.bean("Production Order", p[0])
			production_order.run_method("update_status")
			production_order.run_method("update_produced_qty")

		except StockOverProductionError:
			pass
