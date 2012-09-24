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

# Columns
#----------
from __future__ import unicode_literals
cl = [['Account','Data', '200px'],['Debit/Credit', 'Data', '100px'], ['Group/Ledger', 'Data', '100px'], ['Is PL Account', 'Data', '100px'], ['Opening (Dr)','Data', '100px'], ['Opening (Cr)','Data', '100px'],['Debit', 'Data', '100px'],['Credit', 'Data', '100px'],['Closing (Dr)', 'Data', '100px'],['Closing (Cr)', 'Data', '100px']]
for c in cl:
	colnames.append(c[0])
	coltypes.append(c[1])
	colwidths.append(c[2])
	coloptions.append('')
	col_idx[c[0]] = len(colnames)-1

# transaction date
# ------------------
if not filter_values.get('transaction_date') or not filter_values.get('transaction_date1'):
	msgprint("Please enter From Date and To Date")
	raise Exception
else:
	from_date = filter_values['transaction_date']
	to_date = filter_values['transaction_date1']

#check for from date and to date within same year
#------------------------------------------------
if not sql("select name from `tabFiscal Year` where %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day) and %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day)",(from_date, to_date)):
	msgprint("From Date and To Date must be within same year")
	raise Exception

# get year of the from date and to date
# --------------------------------------
from_date_year = sql("select name from `tabFiscal Year` where %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day)",add_days(from_date, -1))
from_date_year = from_date_year and from_date_year[0][0] or ''

to_date_year = sql("select name from `tabFiscal Year` where %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day)",to_date)
to_date_year = to_date_year and to_date_year[0][0] or ''

# if output is more than 500 lines then it will ask to export
# ------------------------------------------------------------
if len(res) > 1000	and from_export == 0:
	msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please click on 'Export' to open in a spreadsheet")
	raise Exception
	

acc_dict = {}
for t in sql("select name, debit_or_credit, is_pl_account, lft, rgt, group_or_ledger from tabAccount where docstatus != 2 and company = %s", filter_values['company']):
	acc_dict[t[0]] = [t[1], t[2], t[3], t[4], t[5]]


total_debit, total_credit,	total_opening_dr, total_opening_cr, total_closing_dr, total_closing_cr = 0, 0, 0, 0, 0, 0
glc = get_obj('GL Control')

# Main logic
# ----------
for r in res:
	# Fetch account details
	acc = r[col_idx['Account']].strip()
	r.append(acc_dict[acc][0])
	r.append(acc_dict[acc][4])
	r.append(acc_dict[acc][1])
	
	#if shows group and ledger both but without group balance
	if filter_values.get('show_group_ledger') == 'Both But Without Group Balance' and acc_dict[acc][4] == 'Group':
		for i in range(4):
			r.append('')
		continue

	# Opening Balance
	#-----------------------------
	if from_date_year == to_date_year:
		debit_on_fromdate, credit_on_fromdate, opening = glc.get_as_on_balance(acc, from_date_year, add_days(from_date, -1), acc_dict[acc][0], acc_dict[acc][2], acc_dict[acc][3]) # opening = closing of prev_date
	elif acc_dict[acc][1] == 'No': # if there is no previous year in system and not pl account
		opening = sql("select opening from `tabAccount Balance` where account = %s and period = %s", (acc, to_date_year))
		debit_on_fromdate, credit_on_fromdate, opening = 0, 0, flt(opening[0][0])
	else: # if pl account and there is no previous year in system
		debit_on_fromdate, credit_on_fromdate, opening = 0,0,0

	# closing balance
	#--------------------------------
	debit_on_todate, credit_on_todate, closing = glc.get_as_on_balance(acc, to_date_year, to_date, acc_dict[acc][0], acc_dict[acc][2], acc_dict[acc][3])

	# transaction betn the period
	#----------------------------------------

	debit = flt(debit_on_todate) - flt(debit_on_fromdate)
	credit = flt(credit_on_todate) - flt(credit_on_fromdate)
	
	# Debit / Credit
	if acc_dict[acc][0] == 'Credit':
		opening, closing = -1*opening, -1*closing

	# Totals
	total_opening_dr += opening>0 and flt(opening) or 0
	total_opening_cr += opening<0 and -1*flt(opening) or 0
	total_debit += debit
	total_credit += credit
	total_closing_dr += closing>0 and flt(closing) or 0
	total_closing_cr += closing<0 and -1*flt(closing) or 0
	
	# Append in rows
	r.append(flt(opening>0 and opening or 0))
	r.append(flt(opening<0 and -opening or 0))
	r.append(flt(debit))
	r.append(flt(credit))
	r.append(flt(closing>0.01 and closing or 0))
	r.append(flt(closing<-0.01 and -closing or 0))


out =[]
for r in res:
	# Remove accounts if opening bal = debit = credit = closing bal = 0
	# ------------------------------------------------------------------
	if filter_values.get('show_zero_balance') != 'No':
		out.append(r)
	elif r[col_idx['Opening (Dr)']] or r[col_idx['Opening (Cr)']] or r[col_idx['Debit']] or r[col_idx['Credit']] or r[col_idx['Closing (Dr)']] or r[col_idx['Closing (Cr)']] or (r[col_idx['Group/Ledger']] == 'Group' and filter_values.get('show_group_ledger') == 'Both But Without Group Balance'):
		out.append(r)

# Total Debit / Credit
# --------------------------
if filter_values.get('show_group_ledger') in ['Only Ledgers', 'Both But Without Group Balance']:
	t_row = ['' for i in range(len(colnames))]
	t_row[col_idx['Account']] = 'Total'
	t_row[col_idx['Opening (Dr)']] = '%.2f' % total_opening_dr
	t_row[col_idx['Opening (Cr)']] = '%.2f' % total_opening_cr
	t_row[col_idx['Debit']] = '%.2f' % total_debit
	t_row[col_idx['Credit']] = '%.2f' % total_credit
	t_row[col_idx['Closing (Dr)']] = '%.2f' % total_closing_dr
	t_row[col_idx['Closing (Cr)']] = '%.2f' % total_closing_cr
	out.append(t_row)
