def execute():
	import webnotes
	from webnotes.model import delete_doc
	from webnotes.model.code import get_obj
	from webnotes.model.doc import addchild
	
	# delete doctypes and tables
	for dt in ["TDS Payment", "TDS Return Acknowledgement", "Form 16A", 
			"TDS Rate Chart", "TDS Category", "TDS Control", "TDS Detail", 
			"TDS Payment Detail", "TDS Rate Detail", "TDS Category Account",
			"Form 16A Ack Detail", "Form 16A Tax Detail"]:
		delete_doc("DocType", dt)
		
		webnotes.conn.commit()
		webnotes.conn.sql("drop table if exists `tab%s`" % dt)
		webnotes.conn.begin()
			
			
	# Add tds entry in tax table for purchase invoice
	pi_list = webnotes.conn.sql("""select name from `tabPurchase Invoice` 
		where ifnull(tax_code, '')!='' and ifnull(ded_amount, 0)!=0""")
	for pi in pi_list:
		piobj = get_obj("Purchase Invoice", pi[0], with_children=1)
		ch = addchild(piobj.doc, 'taxes_and_charges', 'Purchase Taxes and Charges')
		ch.charge_type = "Actual"
		ch.account_head = piobj.doc.tax_code
		ch.description = piobj.doc.tax_code
		ch.rate = -1*piobj.doc.ded_amount
		ch.tax_amount = -1*piobj.doc.ded_amount
		ch.category = "Total"
		ch.save(1)		
	
	# Add tds entry in entries table for journal voucher
	jv_list = webnotes.conn.sql("""select name from `tabJournal Voucher` 
		where ifnull(tax_code, '')!='' and ifnull(ded_amount, 0)!=0""")
	for jv in jv_list:
		jvobj = get_obj("Journal Voucher", jv[0], with_children=1)
		ch = addchild(jvobj.doc, 'entries', 'Journal Voucher Detail')
		ch.account = jvobj.doc.tax_code
		ch.credit = jvobj.doc.ded_amount
		ch.save(1)