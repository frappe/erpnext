# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	webnotes.conn.sql("""update `tabSingles` set value = '' 
		where doctype  = 'Payment to Invoice Matching Tool' 
		and field in ('account', 'voucher_no', 'total_amount', 'pending_amt_to_reconcile', 
		'from_date', 'to_date', 'amt_greater_than', 'amt_less_than')""")
	