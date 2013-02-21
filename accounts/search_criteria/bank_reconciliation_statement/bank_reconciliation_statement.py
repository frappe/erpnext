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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

#get company
from __future__ import unicode_literals

import webnotes.defaults
company = filter_values.get('company') or webnotes.defaults.get_user_default('company')

# To date
if not filter_values.get('clearance_date1'):
	msgprint('Please enter To Clearance Date')
	raise Exception
else:
	to_date = filter_values['clearance_date1']


#Fiscal year and year start date
#----------------------------------
ysd, fiscal_year = sql("select year_start_date, name from `tabFiscal Year` where %s between year_start_date and date_add(year_start_date,interval 1 year)",to_date)[0]
# Account
if not filter_values.get('account'):
	msgprint('Please select Account in filter section')
	raise Exception
else:
	acc_name = filter_values.get('account')


if len(res) > 300 and from_export == 0:
	msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please select Account or click on 'Export' to open in excel")
	raise Exception

acc = sql("select debit_or_credit, is_pl_account, lft, rgt from tabAccount where name = '%s'" % acc_name)

from accounts.utils import get_balance_on
opening = get_balance_on(acc_name, to_date)

total_debit, total_credit = 0,0
out = []

for r in res:
	total_debit = flt(total_debit) + flt(r[col_idx['Debit']])
	total_credit = flt(total_credit) + flt(r[col_idx['Credit']])
	out.append(r)

if acc and acc[0][0] == 'Debit':
	bank_bal = flt(opening)-flt(total_debit)+flt(total_credit)
else:
	bank_bal = flt(opening)+flt(total_debit)-flt(total_credit)

out.append(['','','','<font color = "#000"><b>Balance as per Company Books: </b></font>', opening,'', ''])
out.append(['','','','<font color = "#000"><b>Amounts not reflected in Bank: </b></font>', total_debit,total_credit,''])
out.append(['','','','<font color = "#000"><b>Balance as per Bank: </b></font>', bank_bal,'',''])
