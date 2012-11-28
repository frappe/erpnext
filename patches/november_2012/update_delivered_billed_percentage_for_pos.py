def execute():
	import webnotes
	from webnotes.model.code import get_obj
	
	sc_obj = get_obj("Sales Common")
	
	si = webnotes.conn.sql("""select distinct si.name 
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si_item.parent = si.name
		and si.docstatus = 1
		and ifnull(si.is_pos, 0) = 1
		and ifnull(si_item.sales_order, '') != ''
	""")
	for d in si:
		sc_obj.update_prevdoc_detail(1, get_obj("Sales Invoice", d[0], with_children=1))