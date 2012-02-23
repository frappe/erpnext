# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# add expense head columns
expense_acc = [c[0] for c in sql("""select distinct expense_head 
									from `tabPV Detail` 
									where parenttype='Payable Voucher' 
									and docstatus=1 
									order by expense_head asc""")]
									
expense_acc.append('Net Total')

for i in expense_acc:
	colnames.append(i)
	coltypes.append('Currency')
	colwidths.append('100px')
	coloptions.append('')

# Add tax head columns
tax_acc = [c[0] for c in sql("""select distinct account_head 
							    from `tabPurchase Tax Detail` 
							    where parenttype = 'Payable Voucher' 
							    and add_deduct_tax = 'Add' 
							    and category in ('For Total', 'For Both')
							    and docstatus=1
							    order by account_head asc""")]
						   
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
	#Get amounts for expense heads
	exp_head_amount = sql("""select expense_head, sum(amount) 
							 from `tabPV Detail` 
							 where parent = %s and parenttype='Payable Voucher'
							 group by expense_head""", (r[col_idx['ID']],))
  
	#convert the result to dictionary for easy retrieval  
	exp_head_amount_dict = {}
	for e in exp_head_amount:
		exp_head_amount_dict[e[0]] = e[1]
  
	exp_head_keys = exp_head_amount_dict.keys()

	net_total = 0
	
	# get expense amount
	for i in expense_acc:
		val = 0
	
		#check if expense head exists in dict
		if i in exp_head_keys:
			val = exp_head_amount_dict[i]
		val = flt(val and val or 0)
		net_total += val
		r.append(val)
		
	r.append(net_total)

	#Get tax for account heads
	acc_head_tax = sql("""select account_head, tax_amount 
						  from `tabPurchase Tax Detail` 
						  where parent = '%s' 
						  and parenttype = 'Payable Voucher' 
						  and add_deduct_tax = 'Add' 
						  and category in ('For Total', 'For Both')""" %(r[col_idx['ID']],))

	#Convert the result to dictionary for easy retrieval
	acc_head_tax_dict = {}
	for a in acc_head_tax:
		acc_head_tax_dict[a[0]] = a[1]
		
	acc_head_keys = acc_head_tax_dict.keys()

	# get tax amount
	total_tax = 0
	grand_total = 0
	for c in tax_acc:
		val = 0
		if c:			
			#check if account head exists in dict
			if c in acc_head_keys:
				val = acc_head_tax_dict[c]		
			val = flt(val and val or 0)
			total_tax += val
			r.append(val)
	r.append(total_tax)
	r.append(flt(total_tax)+ flt(net_total))	# grand total