import webnotes

def execute():
	dn_list = webnotes.conn.sql("""select name from `tabDelivery Note` where docstatus < 2""")
	for dn in dn_list:
		webnotes.bean("Delivery Note", dn[0]).run_method("set_buying_amount")
		
	si_list = webnotes.conn.sql("""select name from `tabSales Invoice` where docstatus < 2""")
	for si in si_list:
		webnotes.bean("Sales Invoice", si[0]).run_method("set_buying_amount")