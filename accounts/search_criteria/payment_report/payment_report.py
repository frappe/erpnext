#check mendatory
if not filter_values.get('posting_date') or not filter_values.get('posting_date1'):
  msgprint("Please select From Posting Date and To Posting Date in 'Set Filters' section")
  raise Exception
else:
  from_date = filter_values.get('posting_date')
  to_date = filter_values.get('posting_date1')

if not filter_values['range_1'] or not filter_values['range_2'] or not filter_values['range_3'] or not filter_values['range_4']:
  msgprint("Please select aging ranges in no of days in 'Set Filters' section")
  raise Exception
  
# ageing based on
aging_based_on = 'Aging Date'
if filter_values.has_key('aging_based_on') and filter_values['aging_based_on']:
  aging_based_on = filter_values['aging_based_on'].split(NEWLINE)[-1]


# Add columns
# -----------
row_list = [['ID','Data','150px',''],
            ['Account','Data','150px',''],
            ['Credit','Data','150px',''],
            ['Debit','Data','150px',''],
            ['Against Payable','Data','150px',''],
            ['Is Advance','Data','150px',''],
            ['Transaction Date','Date','150px',''],
            ['Aging Date','Date','150px',''],
            ['Cheque No','Data','100px',''],
            ['Cheque Date','Date','150px',''],        
            ['Supplier Type','Data','150px',''],
            ['Remark','Data','250px',''],
            ['Advance','Data','250px',''],
            ['PV Transaction Date','Date','150px',''],
            ['PV Aging Date','Date','150px',''],
            ['Age (Days)','Data','100px',''],
            ['0-'+cstr(filter_values['range_1']),'Currency','100px',''],
            [cstr(cint(filter_values['range_1']) + 1)+ '-' +cstr(filter_values['range_2']),'Currency','100px',''],
            [cstr(cint(filter_values['range_2']) + 1)+ '-' +cstr(filter_values['range_3']),'Currency','100px',''],
            [cstr(cint(filter_values['range_3']) + 1)+ '-' +cstr(filter_values['range_4']),'Currency','100px',''],
            [cstr(filter_values['range_4']) + '-Above','Currency','100px','']]  

for r in row_list:
  colnames.append(r[0])
  coltypes.append(r[1])
  colwidths.append(r[2])
  coloptions.append(r[3])
  col_idx[r[0]] = len(colnames)-1
  

for r in res:
  if r[col_idx['Against Payable']]:
    dt=sql("select voucher_date, aging_date from `tabPayable Voucher` where name='%s'"%r[col_idx['Against Payable']])
    r.append('')
    r.append(dt and cstr(dt[0][0]) or '')
    r.append(dt and cstr(dt[0][1]) or '')
  else:
    r.append(r[col_idx['Debit']])
    r.append('')
    r.append('')

  # Aging Credit Amount
  val_l1 = val_l2 = val_l3 = val_l4 = val_l5_above = diff = 0

  if r[col_idx['Against Payable']]:
    amt = flt(r[col_idx['Debit']]) or (-1)*flt(r[col_idx['Credit']])

    if aging_based_on == 'Transaction Date' and r[col_idx['PV Transaction Date']]:
      diff = (getdate(r[col_idx['Transaction Date']]) - getdate(r[col_idx['PV Transaction Date']])).days
    elif aging_based_on == 'Aging Date' and r[col_idx['PV Aging Date']]:
      diff = (getdate(r[col_idx['Aging Date']]) - getdate(r[col_idx['PV Aging Date']])).days
    
    if diff < cint(filter_values['range_1']):
      val_l1 = amt
    if diff >= cint(filter_values['range_1']) and diff < cint(filter_values['range_2']):
      val_l2 = amt
    if diff >= cint(filter_values['range_2']) and diff < cint(filter_values['range_3']):
      val_l3 = amt
    if diff >= cint(filter_values['range_3']) and diff < cint(filter_values['range_4']):
      val_l4 = amt
    if diff >= cint(filter_values['range_4']):
      val_l5_above = amt

  r.append(diff)
  r.append(val_l1)
  r.append(val_l2)
  r.append(val_l3)
  r.append(val_l4)
  r.append(val_l5_above)