from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""
		delete from `tabSingles`
		where doctype='Notification Control'
		and field in (
			'payable_voucher',
			'payment_received_message',
			'payment_sent_message',
			'enquiry')
	""")
	ren_list = [
		['expense_voucher', 'expense_claim'],
		['receivable_voucher', 'sales_invoice'],
		['enquiry', 'opportunity'],
	]
	for r in ren_list:
		webnotes.conn.sql("""
			update `tabSingles`
			set field=%s
			where field=%s
			and doctype='Notification Control'
		""", (r[1], r[0]))
	
	webnotes.conn.commit()
	webnotes.conn.begin()
	webnotes.reload_doc('setup', 'doctype', 'notification_control')