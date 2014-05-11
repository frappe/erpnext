# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	entries = webnotes.conn.sql("""select voucher_type, voucher_no 
		from `tabGL Entry` group by voucher_type, voucher_no""", as_dict=1)
	for entry in entries:
		try:
			cancelled_voucher = webnotes.conn.sql("""select name from `tab%s` where name = %s
				and docstatus=2""" % (entry['voucher_type'], "%s"), entry['voucher_no'])
			if cancelled_voucher:
				webnotes.conn.sql("""delete from `tabGL Entry` where voucher_type = %s and 
					voucher_no = %s""", (entry['voucher_type'], entry['voucher_no']))
		except:
			pass