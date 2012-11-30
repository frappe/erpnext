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

# add additional columns
from __future__ import unicode_literals
from webnotes.utils import flt

cl = [c[0] for c in sql("""select distinct account_head 
						   from `tabSales Taxes and Charges` 
						   where parenttype='Sales Invoice' 
						   and docstatus=1 
						   order by account_head asc""")]

income_acc = [c[0] for c in sql("""select distinct income_account 
								   from `tabSales Invoice Item` 
								   where parenttype='Sales Invoice' 
								   and docstatus=1 
								   order by income_account asc""")]

income_acc.append('Net Total')

for i in income_acc:
	colnames.append(i)
	coltypes.append('Currency')
	colwidths.append('100px')
	coloptions.append('')

cl.append('Total Tax')
cl.append('Grand Total')
for c in cl:
	colnames.append(c)
	coltypes.append('Currency')
	colwidths.append('100px')
	coloptions.append('')
	
income_acc = income_acc[:-1]
cl = cl[:-2]


# add the values
for r in res:

	#Get amounts for income account
	income_acc_list = sql("""select income_account, sum(amount) 
						     from `tabSales Invoice Item` 
						     where parent = %s 
						     and parenttype='Sales Invoice'
						     group by income_account""", (r[col_idx['ID']],))

	#convert the result to dictionary for easy retrieval  
	income_acc_dict = {}
	for ia in income_acc_list:
		income_acc_dict[ia[0]] = flt(ia[1])
	
	net_total = 0
	for i in income_acc:
		val = income_acc_dict.get(i, 0)
		net_total += val
		r.append(val)
	r.append(net_total)

	#Get tax for account heads
	acc_head_tax = sql("""select account_head, sum(tax_amount)
						  from `tabSales Taxes and Charges` 
						  where parent = '%s' 
						  and parenttype = 'Sales Invoice'
						  group by account_head""" %(r[col_idx['ID']],))

	#Convert the result to dictionary for easy retrieval
	acc_head_tax_dict = {}
	for a in acc_head_tax:
		acc_head_tax_dict[a[0]] = flt(a[1])

	total_tax = 0
	for c in cl:
		val = acc_head_tax_dict.get(c, 0)
		total_tax += val
		r.append(val)
	r.append(total_tax)
	r.append(net_total+total_tax)