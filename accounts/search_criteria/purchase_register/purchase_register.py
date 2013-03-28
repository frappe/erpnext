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
from __future__ import unicode_literals
from webnotes.utils import flt

expense_acc = [c[0] for c in sql("""select distinct expense_head 
									from `tabPurchase Invoice Item` 
									where parenttype='Purchase Invoice' 
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
							    from `tabPurchase Taxes and Charges` 
							    where parenttype = 'Purchase Invoice' 
							    and add_deduct_tax = 'Add' 
							    and category in ('Total', 'Valuation and Total')
							    and docstatus=1
							    order by account_head asc""")]
						   
tax_acc.append('Total Tax')
tax_acc.append('Grand Total')

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
							 from `tabPurchase Invoice Item` 
							 where parent = %s and parenttype='Purchase Invoice'
							 group by expense_head""", (r[col_idx['ID']]))
  
	#convert the result to dictionary for easy retrieval  
	exp_head_amount_dict = {}
	for e in exp_head_amount:
		exp_head_amount_dict[e[0]] = e[1]
  
	net_total = 0	
	# get expense amount
	for i in expense_acc:
		val = exp_head_amount_dict.get(i, 0)
		net_total += val
		r.append(val)		
	r.append(net_total)

	#Get tax for account heads
	acc_head_tax = sql("""select account_head, 
		sum(if(add_deduct_tax='Add', tax_amount, -tax_amount)) 
		from `tabPurchase Taxes and Charges` where parent = %s and parenttype = 'Purchase Invoice' 
		and category in ('Total', 'Valuation and Total') group by account_head""", r[col_idx['ID']])

	#Convert the result to dictionary for easy retrieval
	acc_head_tax_dict = {}
	for a in acc_head_tax:
		acc_head_tax_dict[a[0]] = flt(a[1])
		
	# get tax amount
	total_tax = 0
	for c in tax_acc:	
		val = acc_head_tax_dict.get(c, 0)
		total_tax += val
		r.append(val)
	r.append(total_tax)
	r.append(flt(total_tax)+ flt(net_total))	# grand total