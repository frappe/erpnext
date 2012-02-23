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

# columns
colnames[0] = 'Account'
col_idx['Account'] = 0
coltypes[0] = 'Link'
coloptions[0] =  'Account'
colwidths[0] = '200px'

cl = [['Debit', 'Data', '100px'],['Credit', 'Data', '100px']]
for c in cl:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append('')
  col_idx[c[0]] = len(colnames)-1
  

# transaction date
if not filter_values.get('transaction_date') or not filter_values.get('transaction_date1'):
  msgprint("Please enter From Date and To Date")
  raise Exception
else:
  from_date = add_days(filter_values['transaction_date'], -1)
  to_date = filter_values['transaction_date1']

# if output is more than 300 lines then it will ask to export
if len(res) > 300  and from_export == 0:
  msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please click on 'Export' to open in a spreadsheet")
  raise Exception

total_debit, total_credit = 0,0

for r in res:
  amount = sql("select sum(debit), sum(credit) from `tabGL Entry` WHERE posting_date >= '%s' AND posting_date <= '%s' and ifnull(is_opening,'No') = 'No' AND account = '%s' AND ifnull(is_cancelled, 'No') = 'No'" % (from_date,to_date, r[col_idx['Account']].strip()))
  total_debit = flt(total_debit) + flt(amount[0][0])
  total_credit = flt(total_credit) + flt(amount[0][1])

  r.append(flt(amount[0][0]))
  r.append(flt(amount[0][1]))

t_row = ['' for i in range(len(colnames))]
t_row[col_idx['Account']] = 'Total'
t_row[col_idx['Debit']] = total_debit
t_row[col_idx['Credit']] = total_credit
res.append(t_row)