
# Check mandatory filters
#------------------------------
if not filter_values.get('posting_date') or not filter_values.get('posting_date1'):
  msgprint("Please select From Posting Date and To Posting Date in 'Set Filters' section")
  raise Exception
else:
  from_date = filter_values.get('posting_date')
  to_date = filter_values.get('posting_date1')

if not filter_values['range_1'] or not filter_values['range_2'] or not filter_values['range_3'] or not filter_values['range_4']:
  msgprint("Please select aging ranges in no of days in 'Set Filters' section")
  raise Exception

# validate Range
range_list = ['range_1','range_2','range_3','range_4']
for r in range(len(range_list)-1):
  if not cint(filter_values[range_list[r]]) < cint(filter_values[range_list[r + 1]]):
    msgprint("Range %s should be less than Range %s." % (cstr(r+1),cstr(r+2)))
    raise Exception


# Add columns
# -----------
data = [['Transaction Date','Date','80px',''],
        ['Aging Date','Date','80px',''],
        ['Account','Data','120px',''],
        ['Against Voucher Type','Data','120px',''],
        ['Against Voucher','Data','120px',''],
        ['Voucher Type','Data','120px',''],
        ['Voucher No','Data','120px',''],
        ['Remarks','Data','160px',''],
        ['Territory','Data','120px',''],
        ['Due Date', 'Date', '80px', ''],
        ['Opening Amt','Currency','120px',''],
        ['Outstanding Amt','Currency','120px',''],
        ['Age (Days)', 'Data', '60px', ''],
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
aging_based_on = filter_values.get('aging_based_on') and filter_values['aging_based_on'].split(NEWLINE)[-1] or 'Aging Date'

if  len(res) > 600 and from_export == 0:
  msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please select Account or click on 'Export' to open in excel")
  raise Exception

# ------------------------------------------------------------------
# main loop starts here
# ------------------------------------------------------------------

out = []
total_opening_amt,total_outstanding_amt = 0,0
for r in res:
  # get customer territory
  terr = sql("select t1.territory from `tabCustomer` t1, `tabAccount` t2 where t1.name = t2.master_name and t2.name = '%s'" % r[col_idx['Account']])
  r.append(terr and terr[0][0] or '')
  
  outstanding_amt, opening_amt, cond, due_date = 0,0, '', ''
  # if entry against Receivable Voucher
  if r[col_idx['Against Voucher']] and r[col_idx['Voucher Type']] == 'Receivable Voucher':
    # get due date
    due_date = sql("select due_date from `tabReceivable Voucher` where name = '%s'" % r[col_idx['Against Voucher']])
    due_date = due_date and cstr(due_date[0][0]) or ''

    # get booking amt
    opening_amt = sql("select debit from `tabGL Entry` where account = '%s' and voucher_no = '%s' and is_cancelled = 'No'" % (r[col_idx['Account']], r[col_idx['Voucher No']]))
    opening_amt = opening_amt and flt(opening_amt[0][0]) or 0

    cond =  "and against_voucher = '%s' and against_voucher is not null" % r[col_idx['Against Voucher']]

  # if entry against JV & and not adjusted within period
  elif r[col_idx['Against Voucher Type']] == 'Receivable Voucher' and sql("select name from `tabReceivable Voucher` where name = '%s' and (posting_date < '%s' or posting_date > '%s') and docstatus = 1" % (r[col_idx['Against Voucher']], from_date, to_date)):
    cond = " and voucher_no = '%s' and ifnull(against_voucher, '') = '%s'" % (r[col_idx['Voucher No']], r[col_idx['Against Voucher']])
  # if entry against JV and unadjusted
  elif not r[col_idx['Against Voucher']]:
    cond = " and ((voucher_no = '%s' and ifnull(against_voucher, '') = '') or (ifnull(against_voucher, '') = '%s' and voucher_type = 'Journal Voucher'))" % (r[col_idx['Voucher No']], r[col_idx['Voucher No']])
  
  if cond:
    outstanding_amt = flt(sql("select ifnull(sum(debit),0) - ifnull(sum(credit),0) from `tabGL Entry` where account = '%s' and ifnull(is_cancelled, 'No') = 'No' and posting_date <= '%s' %s" % (r[col_idx['Account']], to_date, cond))[0][0] or 0)
    # add to total outstanding
    total_outstanding_amt += flt(outstanding_amt)
    # add to total booking amount
    if outstanding_amt and r[col_idx['Voucher Type']] == 'Receivable Voucher' and r[col_idx['Against Voucher']]:
      total_opening_amt += flt(opening_amt)

  r += [due_date, opening_amt, outstanding_amt]

  #Ageing Outstanding
  val_l1 = val_l2 = val_l3 = val_l4 = val_l5_above = 0
  diff = 0
  if r[col_idx[aging_based_on]]:
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

if  len(out) > 300 and from_export == 0:
  msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please select Account or click on 'Export' to open in excel")
  raise Exception

# Append Extra rows to RES
if len(out) > 0:
  t_row = ['' for i in range(len(colnames))]
  t_row[col_idx['Voucher No']] = 'Total'
  t_row[col_idx['Opening Amt']] = total_opening_amt
  t_row[col_idx['Outstanding Amt']] = total_outstanding_amt
  out.append(t_row)
