# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	
	webnotes.conn.sql("""update `tabGL Entry` 
		set debit = round(debit, 2), credit = round(credit, 2)""")

	gle = webnotes.conn.sql("""select voucher_type, voucher_no, 
		sum(ifnull(debit,0)) - sum(ifnull(credit, 0)) as diff 
	    from `tabGL Entry`
		group by voucher_type, voucher_no
		having sum(ifnull(debit, 0)) != sum(ifnull(credit, 0))""", as_dict=1)

	for d in gle:
		webnotes.conn.sql("""update `tabGL Entry` set debit = debit - %s 
			where voucher_type = %s and voucher_no = %s and debit > 0 limit 1""", 
			(d['diff'], d['voucher_type'], d['voucher_no']))