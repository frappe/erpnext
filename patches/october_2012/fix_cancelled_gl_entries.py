# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	entries = webnotes.conn.sql("""select voucher_type, voucher_no 
		from `tabGL Entry` group by voucher_type, voucher_no""", as_dict=1)
	for entry in entries:
		try:
			docstatus = webnotes.conn.sql("""select docstatus from `tab%s` where name = %s
				and docstatus=2""" % (entry['voucher_type'], "%s"), entry['voucher_no'])
			is_cancelled = docstatus and 'Yes' or None
			if is_cancelled:
				webnotes.conn.sql("""update `tabGL Entry` set is_cancelled = 'Yes'
					where voucher_type = %s and voucher_no = %s""", 
					(entry['voucher_type'], entry['voucher_no']))
		except Exception, e:
			pass