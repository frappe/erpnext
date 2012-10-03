def execute():
	import webnotes
	vouchers = webnotes.conn.sql("""
		select parent, parenttype, modified from `tabPurchase Taxes and Charges`
		where modified >= '2012-07-12'
		and category = 'Valuation' and tax_amount != 0
		and parenttype != 'Purchase Taxes and Charges Master'
	""")
	print vouchers