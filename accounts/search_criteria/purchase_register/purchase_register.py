# add expense head columns
expense_acc = [c[0] for c in sql("select distinct expense_head from `tabPV Detail` where parenttype='Payable Voucher' and docstatus=1 order by idx asc")]
expense_acc.append('Net Total')

for i in expense_acc:
	colnames.append(i)
	coltypes.append('Currency')
	colwidths.append('100px')
	coloptions.append('')

# Add tax head columns
tax_acc = [c[0] for c in sql("select distinct account_head from `tabPurchase Tax Detail` where parenttype='Payable Voucher' and category in ('For Total', 'For Both') and add_deduct_tax = 'Add' and docstatus=1 order by idx asc")]
tax_acc.append('Total Tax')
tax_acc.append('GrandTotal')

for c in tax_acc:
	if c:
		colnames.append(c)
		coltypes.append('Currency')
		colwidths.append('100px')
		coloptions.append('')

# remove total columns from the list
expense_acc = expense_acc[:-1]
tax_acc = tax_acc[:-2]

# add the values
for r in res:
	net_total = 0
	
	# get expense amount
	for i in expense_acc:
		val = sql("select sum(amount) from `tabPV Detail` where parent = %s and parenttype='Payable Voucher' and expense_head = %s", (r[col_idx['ID']], i))
		val = flt(val and val[0][0] or 0)
		net_total += val
		r.append(val)
	r.append(net_total)

	# get tax amount
	total_tax = 0
	grand_total = 0
	for c in tax_acc:
		if c:
			val = sql("select tax_amount from `tabPurchase Tax Detail` where parent = %s and parenttype='Payable Voucher' and account_head = %s and	category in ('For Total', 'For Both') and add_deduct_tax = 'Add'", (r[col_idx['ID']], c))
			val = flt(val and val[0][0] or 0)
			total_tax += val
			r.append(val)
	r.append(total_tax)
	r.append(total_tax+net_total)	# grand total
