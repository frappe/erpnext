# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from webnotes.utils import flt
	
	records = webnotes.conn.sql("""select name, grand_total, debit_to from `tabSales Invoice` 
		where docstatus = 1""", as_dict=1)
	
	for r in records:
		gle = webnotes.conn.sql("""select name, debit from `tabGL Entry` 
			where account = %s and voucher_type = 'Sales Invoice' and voucher_no = %s
			and ifnull(is_cancelled, 'No') = 'No' limit 1""", (r.debit_to, r.name), as_dict=1)
		if gle:
			diff = flt((flt(r.grand_total) - flt(gle[0]['debit'])), 2)
		
			if abs(diff) == 0.01:
				# print r.name, r.grand_total, gle[0]['debit'], diff
				webnotes.conn.sql("""update `tabGL Entry` set debit = debit + %s 
					where name = %s""", (diff, gle[0]['name']))
				
				webnotes.conn.sql("""update `tabGL Entry` set credit = credit - %s
					where voucher_type = 'Sales Invoice' and voucher_no = %s 
					and credit > 0 limit 1""", (diff, r.name))