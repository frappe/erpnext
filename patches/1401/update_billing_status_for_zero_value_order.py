# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import flt

def execute():
	for order_type in ["Sales", "Purchase"]:
		for d in webnotes.conn.sql("""select par.name, sum(ifnull(child.qty, 0)) as total_qty 
			from `tab%s Order` par, `tab%s Order Item` child  
			where par.name = child.parent and par.docstatus = 1 
			and ifnull(par.net_total, 0) = 0 group by par.name""" % 
			(order_type, order_type), as_dict=1):
				
				billed_qty = flt(webnotes.conn.sql("""select sum(ifnull(qty, 0)) 
					from `tab%s Invoice Item` where %s=%s and docstatus=1""" % 
					(order_type, "sales_order" if order_type=="Sales" else "purchase_order", '%s'), 
					(d.name))[0][0])
				
				per_billed = ((d.total_qty if billed_qty > d.total_qty else billed_qty)\
					/ d.total_qty)*100
				webnotes.conn.set_value(order_type+ " Order", d.name, "per_billed", per_billed)
				
				if order_type == "Sales":
					if per_billed < 0.001: billing_status = "Not Billed"
					elif per_billed >= 99.99: billing_status = "Fully Billed"
					else: billing_status = "Partly Billed"
	
					webnotes.conn.set_value("Sales Order", d.name, "billing_status", billing_status)