# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	
	si = webnotes.conn.sql("""select distinct si.name 
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si_item.parent = si.name
		and si.docstatus = 1
		and ifnull(si.is_pos, 0) = 1
		and ifnull(si_item.sales_order, '') != ''
	""")
	for d in si:
		webnotes.bean("Sales Invoice", d[0]).run_method("update_qty")