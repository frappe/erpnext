import webnotes

def execute():
	"""
		To Hide Net Total, Grand Total Export and Rounded Total Export on checking print hide
		
		Uncheck print_hide for fields:
			net_total, grand_total_export and rounded_total_export
		For DocType(s):
			* Receivable Voucher
			* Sales Order
			* Delivery Note
			* Quotation
	"""
	webnotes.conn.sql("""\
		UPDATE tabDocField
		SET print_hide = 0
		WHERE fieldname IN ('net_total', 'grand_total_export', 'rounded_total_export')
		AND parent IN ('Receivable Voucher', 'Sales Order', 'Delivery Note', 'Quotation')
	""")
