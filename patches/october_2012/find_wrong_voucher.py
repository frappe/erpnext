def execute():
	import webnotes
	from webnotes.utils import flt
	vouchers = webnotes.conn.sql("""
		select parent, parenttype, modified, sum(if(add_deduct_tax='Add', tax_amount, -tax_amount)) as tax from `tabPurchase Taxes and Charges`
		where modified >= '2012-07-12'
		and category in ('Total', 'Valuation and Total')
		and parenttype != 'Purchase Taxes and Charges Master'
		group by parenttype, parent
	""")
	
	for d in vouchers:
		total_tax = webnotes.conn.sql("""select total_tax from `tab%s` where name = %s""" %
			(d[1], '%s'), d[0])
		if flt(total_tax[0][0]) != flt(d[3]):
			print d