# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "stock_ledger_entry")
	
	# from stock entry
	webnotes.conn.sql("""update 
		`tabStock Ledger Entry` sle, 
		`tabStock Entry` st
	set sle.project = st.project_name
	where
	 	sle.voucher_type = "Stock Entry"
		and sle.voucher_no = st.name""")
			
	# from purchase
	webnotes.conn.sql("""update 
		`tabStock Ledger Entry` sle, 
		`tabPurchase Receipt Item` pri
	set sle.project = pri.project_name
	where
	 	sle.voucher_type = "Purchase Receipt"
		and sle.voucher_detail_no = pri.name""")

	# from delivery note
	webnotes.conn.sql("""update 
		`tabStock Ledger Entry` sle, 
		`tabDelivery Note` dn
	set sle.project = dn.project_name
	where
	 	sle.voucher_type = "Delivery Note"
		and sle.voucher_no = dn.name""")
		
	# from pos invoice
	webnotes.conn.sql("""update 
		`tabStock Ledger Entry` sle, 
		`tabSales Invoice` si
	set sle.project = si.project_name
	where
	 	sle.voucher_type = "Sales Invoice"
		and sle.voucher_no = si.name""")
	
	