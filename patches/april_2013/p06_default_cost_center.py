import webnotes

def execute():
	for dt, fieldname in \
		(("Journal Voucher Detail", "cost_center"), 
		("Sales Taxes and Charges", "cost_center_other_charges"), 
		("Purchase Taxes and Charges", "cost_center"), ("Delivery Note Item", "cost_center"),
		("Purchase Invoice Item", "cost_center"), ("Sales Invoice Item", "cost_center")):
			webnotes.conn.sql_ddl("""alter table `tab%s` alter `%s` drop default""" % (dt, fieldname))
			webnotes.reload_doc(webnotes.conn.get_value("DocType", dt, "module"), "DocType", dt)
