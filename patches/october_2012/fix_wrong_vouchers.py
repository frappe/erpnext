def execute():
	import webnotes
	from webnotes.utils import flt
	from webnotes.model.code import get_obj

	vouchers = webnotes.conn.sql("""
		select 
			parent, parenttype, modified, 
			sum(if(category in ('Valuation and Total', 'Total') and add_deduct_tax='Add',
 				tax_amount, 0)) as tax_added, 
			sum(if(category in ('Valuation and Total', 'Total') and add_deduct_tax='Deduct', 
 				tax_amount, 0)) as tax_ded
		from 
			`tabPurchase Taxes and Charges`
		where 
			modified >= '2012-07-12'
			and parenttype != 'Purchase Taxes and Charges Master'
			and parent not like 'old_p%'
			and docstatus != 2
		group by parenttype, parent
		order by modified
	""", as_dict=1)

	for d in vouchers:
		current_total_tax = webnotes.conn.sql("""select total_tax from `tab%s` where name = %s""" %
			(d['parenttype'], '%s'), d['parent'])
		correct_total_tax = flt(d['tax_added']) - flt(d['tax_ded'])
		
		if flt(current_total_tax[0][0]) != correct_total_tax:
			if d['parenttype'] == 'Purchase Invoice':
				webnotes.conn.sql("""
					update `tab%s` 
					set 
						total_tax = %s, 
						other_charges_added = %s, 
						other_charges_added_import = other_charges_added / conversion_rate, 
						other_charges_deducted = %s, 
						other_charges_deducted_import = other_charges_deducted / conversion_rate, 
						grand_total = net_total + other_charges_added - other_charges_deducted,
						grand_total_import = grand_total / conversion_rate, 
						total_amount_to_pay = grand_total - total_tds_on_voucher,
						outstanding_amount = total_amount_to_pay - total_advance
					where 
						name = %s
				""" % (d['parenttype'], '%s', '%s', '%s', '%s'), 
					(correct_total_tax, d['tax_added'], d['tax_ded'], d['parent']))
					
				# post gl entry
				webnotes.conn.sql("""update `tabGL Entry` set is_cancelled = 'No' 
					where voucher_type = %s and voucher_no = %s""", 
					(d['parenttype'], d['parent']))
				obj = get_obj(d['parenttype'], d['parent'], with_children=1)
				obj.make_gl_entries()
				
			else:
				webnotes.conn.sql("""
					update `tab%s` 
					set 
						total_tax = %s, 
						grand_total = net_total + total_tax, 
						grand_total_import = grand_total / conversion_rate
					where 
						name = %s
				""" % (d[1], '%s', '%s'), (correct_total_tax, d['parent']))