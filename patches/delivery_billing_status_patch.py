import webnotes
sql = webnotes.conn.sql

# update SO
#---------------
def update_percent():
	so = sql("select name from 	`tabSales Order` where docstatus = 1")
	for d in so:
		sql("""
			update 
				`tabSales Order` 
			set 
				per_delivered = (select sum(if(qty > ifnull(delivered_qty, 0), delivered_qty, qty))/sum(qty)*100 from `tabSales Order Detail` where parent='%s'), 
				per_billed = (select sum(if(qty > ifnull(billed_qty, 0), billed_qty, qty))/sum(qty)*100 from `tabSales Order Detail` where parent='%s') 
			where 
				name='%s'""" % (d[0], d[0], d[0]))

	# update DN	
	# ---------
	dn = sql("select name from 	`tabDelivery Note` where docstatus = 1")
	for d in dn:
		sql("""
			update 
				`tabDelivery Note` 
			set 
				per_billed = (select sum(if(qty > ifnull(billed_qty, 0), billed_qty, qty))/sum(qty)*100 from `tabDelivery Note Detail` where parent='%s') 
			where 
				name='%s'""" % (d[0], d[0]))
	

# update delivery/billing status 
#-------------------------------
def update_status():
	sql("""update `tabSales Order` set delivery_status = if(ifnull(per_delivered,0) < 0.001, 'Not Delivered', 
			if(per_delivered >= 99.99, 'Fully Delivered', 'Partly Delivered'))""")
	sql("""update `tabSales Order` set billing_status = if(ifnull(per_billed,0) < 0.001, 'Not Billed', 
			if(per_billed >= 99.99, 'Fully Billed', 'Partly Billed'))""")
	sql("""update `tabDelivery Note` set billing_status = if(ifnull(per_billed,0) < 0.001, 'Not Billed', 
			if(per_billed >= 99.99, 'Fully Billed', 'Partly Billed'))""")
			
def run_patch():
	update_percent()
	update_status()
