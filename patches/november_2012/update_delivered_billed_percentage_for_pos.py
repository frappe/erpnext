# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from webnotes.model.code import get_obj
	
	#sc_obj = get_obj("Sales Common")
	from selling.doctype.sales_common import sales_common
	
	si = webnotes.conn.sql("""select distinct si.name 
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si_item.parent = si.name
		and si.docstatus = 1
		and ifnull(si.is_pos, 0) = 1
		and ifnull(si_item.sales_order, '') != ''
	""")
	for d in si:
		sales_common.StatusUpdater(get_obj("Sales Invoice", d[0], with_children=1), \
		 	1).update_all_qty()