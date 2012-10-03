def execute():
	import webnotes
	vouchers = webnotes.conn.sql("""
		select parent, parenttype, modified from `tabPurchase Taxes and Charges`
		where modified >= '2012-10-02'
		and (category = 'Total' or category = 'Valuation')
		and parenttype != 'Purchase Taxes and Charges Master'
	""")
	print vouchers