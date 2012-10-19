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

# Check mandatory filters
# ------------------------------------------------------------------

from __future__ import unicode_literals
if not filter_values.get('posting_date1'):
	msgprint("Please select To Posting Date ")
	raise Exception
else:
	to_date = filter_values.get('posting_date1')

if not filter_values['range_1'] or not filter_values['range_2'] \
		or not filter_values['range_3'] or not filter_values['range_4']:
	msgprint("Please select aging ranges in no of days in 'More Filters' ")
	raise Exception

# validate Range
range_list = ['range_1','range_2','range_3','range_4']
for r in range(len(range_list)-1):
	if not cint(filter_values[range_list[r]]) < cint(filter_values[range_list[r + 1]]):
		msgprint("Range %s should be less than Range %s." % (cstr(r+1),cstr(r+2)))
		raise Exception

	
# Add columns
# ------------------------------------------------------------------
data = [['Aging Date','Date','80px',''],
		['Account','Data','120px',''],
		['Against Voucher Type','Data','120px',''],
		['Against Voucher','Data','120px',''],
		['Voucher Type','Data','120px',''],
		['Voucher No','Data','120px',''],
		['Remarks','Data','160px',''],
		['Supplier Type', 'Data', '80px', ''],
		['Due Date', 'Data', '80px', ''],
		['Bill No','Data','80px',''],
		['Bill Date','Data','80px',''],
		['Opening Amt','Currency','120px',''],
		['Outstanding Amt','Currency','120px',''],
		['Age (Days)', 'Currency', '150px', ''],
		['0-'+cstr(filter_values['range_1']),'Currency','100px',''],
		[cstr(cint(filter_values['range_1']) + 1)+ '-' +cstr(filter_values['range_2']),'Currency','100px',''],
		[cstr(cint(filter_values['range_2']) + 1)+ '-' +cstr(filter_values['range_3']),'Currency','100px',''],
		[cstr(cint(filter_values['range_3']) + 1)+ '-' +cstr(filter_values['range_4']),'Currency','100px',''],
		[cstr(filter_values['range_4']) + '-Above','Currency','100px','']]
				

for d in data:
	colnames.append(d[0])
	coltypes.append(d[1])
	colwidths.append(d[2])
	coloptions.append(d[3])
	col_idx[d[0]] = len(colnames)-1
	
# ageing based on
# ------------------------------------------------------------------
aging_based_on = 'Aging Date'
if filter_values.has_key('aging_based_on') and filter_values['aging_based_on']:
	aging_based_on = filter_values['aging_based_on'].split(NEWLINE)[-1]

if	len(res) > 2000 and from_export == 0:
	msgprint("""This is a very large report and cannot be shown in the browser 
		as it is likely to make your browser very slow.
		Please select Account or click on 'Export' to open in excel""", raise_exception=1)

# get supplier type
supp_type_dict = {}
for each in sql("""select t2.name, t1.supplier_type from tabSupplier t1, tabAccount t2 
		where t1.name = t2.account_name group by t2.name"""):
	supp_type_dict[each[0]] = each[1]

# get due_date, bill_no, bill_date from PV
pv_dict = {}
for t in sql("""select name, due_date, bill_no, bill_date 
		from `tabPurchase Invoice` group by name"""):
	pv_dict[t[0]] = [cstr(t[1]), t[2], cstr(t[3])]

# pv after to-date
pv_after_to_date = [d[0] for d in sql("""select distinct name from `tabPurchase Invoice` 
	where posting_date > %s and docstatus = 1""", (to_date,))]


from webnotes.utils import nowdate

out = []
total_booking_amt, total_outstanding_amt = 0,0

for r in res:
	outstanding_amt, due_date, bill_no, bill_date, cond = 0, '','','', ''
	booking_amt = r.pop(7)
	
	# supplier type
	r.append(supp_type_dict.get(r[col_idx['Account']], ''))
	
	if r[col_idx['Voucher Type']] == 'Purchase Invoice':
		r += pv_dict.get(r[col_idx['Voucher No']], ['', '', ''])
	else:
		r += ['', '', '']
	
	# if entry against Purchase Invoice
	if r[col_idx['Against Voucher']] and r[col_idx['Voucher Type']] == 'Purchase Invoice':
		cond = " and ifnull(against_voucher, '') = '%s'" % r[col_idx['Against Voucher']]

	# if entry against JV & and not adjusted within period
	elif r[col_idx['Against Voucher Type']] == 'Purchase Invoice' \
			and r[col_idx['Against Voucher']] in pv_after_to_date:
		booking_amt = 0
		cond = """ and voucher_no = '%s' and ifnull(against_voucher, '') = '%s'""" \
		 	% (r[col_idx['Voucher No']], r[col_idx['Against Voucher']])
	
	# if un-adjusted
	elif not r[col_idx['Against Voucher']]:
		booking_amt = 0
		cond = """ and ((voucher_no = '%s' and ifnull(against_voucher, '') = '') 
			or (ifnull(against_voucher, '') = '%s' and voucher_type = 'Journal Voucher'))""" \
			% (r[col_idx['Voucher No']], r[col_idx['Voucher No']])

	if cond:
		outstanding_amt = flt(sql("""select sum(ifnull(credit, 0))-sum(ifnull(debit, 0)) 
			from `tabGL Entry` where account = %s and ifnull(is_cancelled, 'No') = 'No' 
			and posting_date <= %s %s"""
			% ('%s', '%s', cond), (r[col_idx['Account']], to_date,))[0][0] or 0)

		# add to total outstanding
		total_outstanding_amt += flt(outstanding_amt)

		# add to total booking amount
		if outstanding_amt and r[col_idx['Voucher Type']] == 'Purchase Invoice' \
				and r[col_idx['Against Voucher']]:
			total_booking_amt += flt(booking_amt)

	r += [booking_amt, outstanding_amt]
	
	# split into date ranges
	val_l1 = val_l2 = val_l3 = val_l4 = val_l5_above= 0
	if r[col_idx[aging_based_on]]:
		if getdate(to_date) > getdate(nowdate()):
			to_date = nowdate()
		diff = (getdate(to_date) - getdate(r[col_idx[aging_based_on]])).days
		if diff < cint(filter_values['range_1']):
			val_l1 = outstanding_amt
		if diff >= cint(filter_values['range_1']) and diff < cint(filter_values['range_2']):
			val_l2 = outstanding_amt
		if diff >= cint(filter_values['range_2']) and diff < cint(filter_values['range_3']):
			val_l3 = outstanding_amt
		if diff >= cint(filter_values['range_3']) and diff < cint(filter_values['range_4']):
			val_l4 = outstanding_amt
		if diff >= cint(filter_values['range_4']):
			val_l5_above = outstanding_amt

	r += [diff, val_l1, val_l2, val_l3, val_l4, val_l5_above]

	# Only show that entry which has outstanding
	if abs(flt(outstanding_amt)) > 0.001:
		out.append(r)
		
if	len(out) > 300 and from_export == 0:
	msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please select Account or click on 'Export' to open in excel")
	raise Exception


# Append Extra rows to RES
# ------------------------------------------------------------------
t_row = ['' for i in range(len(colnames))]
t_row[col_idx['Voucher No']] = 'Total'
t_row[col_idx['Opening Amt']] = total_booking_amt
t_row[col_idx['Outstanding Amt']] = total_outstanding_amt
out.append(t_row)
