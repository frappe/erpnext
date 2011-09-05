# Add columns
# -----------
row_list = [['Date', 'Date', '150px', '']
           ,['ARI/INVOICE/Other Approved document/Bill of entry No.', 'Date', '150px', '']
           ,['Date', 'Date', '150px', '']
           ,['Baisc Excise Duty', 'Currency', '150px', '']
           ,['Additional Duty', 'Currency', '150px', '']
           ,['Education Cess', 'Currency', '150px', '']
           ,['S.H.Education Cess', 'Currency', '150px', '']
           ,[' Basic Excise Duty', 'Currency', '150px', '']
           ,[' Education Cess', 'Currency', '150px', '']
           ,[' S.H.Education Cess', 'Currency', '150px', '']
           ,['Basic Excise Duty ', 'Currency', '150px', '']
           ,['Education Cess ', 'Currency', '150px', '']
           ,['S.H.Education Cess ', 'Currency', '150px', '']
           ,['Remarks', 'Data', '150px', '']
]

if not filter_values['report']:
  msgprint("Please Select Report Type. ")
  raise Exception

if 'CAPITAL' not in filter_values['report']:
  row_list.insert(3,['Range/ Divsion/ Custom House from where received', 'Data', '150px', ''])
  row_list.insert(4,['Folio No. & Entry No. in Part I', 'Data', '150px', ''])
  row_list.insert(7,['CVD', 'Currency', '150px', ''])
  row_list.insert(10,['ARI/INVOICE/ Other Approved document/Bill of entry No.', 'Data', '100px', ''])
  row_list.insert(11,['Date', 'Date', '150px', ''])
elif 'CAPITAL' in filter_values['report']:
  row_list.insert(7,[' Basic Excise Duty ', 'Currency', '150px', ''])
  row_list.insert(8,[' Education Cess ', 'Currency', '150px', ''])
  row_list.insert(9,[' S.H.Education Cess ', 'Currency', '150px', ''])
  row_list.insert(10,['ARI/INVOICE/ Other Approved document/Bill of entry No.', 'Data', '100px', ''])
  row_list.insert(11,['Date', 'Date', '150px', ''])

for r in row_list:
  colnames.append(r[0])
  coltypes.append(r[1])
  colwidths.append(r[2])
  coloptions.append(r[3])
  col_idx[r[0]] = len(colnames)-1


# get as_on_date for opening
as_on_date = ''
if filter_values.get('posting_date'):
  as_on_date = add_days(filter_values['posting_date'], -1)

ysd, from_date_year = sql("select year_start_date, name from `tabFiscal Year` where %s between year_start_date and date_add(year_start_date,interval 1 year)",as_on_date)[0]


# Get Opening Balance
def get_opening_balance(acc, fy, as_on_date, ysd, get_opening_balance, get_obj):
  glc = get_obj('GL Control')
  acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt, group_or_ledger from tabAccount where name = '%s'" % acc)
  return glc.get_as_on_balance(acc, fy, as_on_date, acc_det[0][0], acc_det[0][2], acc_det[0][3])[2]

cum_sum_main_acc_head = cum_sum_add_acc_head = cum_sum_cvd_acc_head = cum_sum_edu_cess_acc_head = cum_sum_sh_edu_cess_acc_head = 0
openg_main_acc_head = openg_add_acc_head = openg_cvd_acc_head = openg_edu_cess_acc_head = openg_sh_edu_cess_acc_head = 0

# Get Opening of Basic Excise Duty
if not filter_values['main_acc_head']: 
  msgprint("Please Enter Main Account Head")
  raise Exception
cum_sum_main_acc_head = openg_main_acc_head = get_opening_balance(filter_values['main_acc_head'], from_date_year, as_on_date, ysd, get_opening_balance, get_obj)

# Get Opening of add_acc_head
if filter_values['add_acc_head'] : cum_sum_add_acc_head = openg_add_acc_head = get_opening_balance(filter_values['add_acc_head'], from_date_year, as_on_date, ysd, get_opening_balance, get_obj)

# Get Opening of cvd_acc_head
if filter_values['cvd_acc_head'] : cum_sum_cvd_acc_head = openg_cvd_acc_head = get_opening_balance(get_opening_balance, filter_values['cvd_acc_head'], from_date_year, as_on_date, ysd, get_opening_balance, get_obj)

# Get Opening of edu_cess_acc_head
if not filter_values['edu_cess_acc_head'] :
  msgprint("Please Enter Edu Cess Account Head")
  raise Exception
cum_sum_edu_cess_acc_head = openg_edu_cess_acc_head = get_opening_balance(filter_values['edu_cess_acc_head'], from_date_year, as_on_date, ysd, get_opening_balance, get_obj)

# Get Opening of sh_edu_cess_acc_head
if not filter_values['sh_edu_cess_acc_head'] :
  msgprint("Please Enter S.H.Edu Cess Account Head")
  raise Exception
cum_sum_sh_edu_cess_acc_head = openg_sh_edu_cess_acc_head = get_opening_balance(filter_values['sh_edu_cess_acc_head'], from_date_year, as_on_date, ysd, get_opening_balance, get_obj)


for r in res:
  remarks = r[col_idx['ARI/INVOICE/ Other Approved document/Bill of entry No.']]
  r[col_idx['ARI/INVOICE/ Other Approved document/Bill of entry No.']] = ''
  r.append('')
  if 'CAPITAL' not in filter_values['report']:
    r.append(0.00)
    r.append(0.00)
    r.append(0.00)
    cum_sum_main_acc_head = flt(cum_sum_main_acc_head) + flt(r[col_idx['Baisc Excise Duty']])
    cum_sum_add_acc_head = flt(cum_sum_add_acc_head) + flt(r[col_idx['Additional Duty']])
    cum_sum_cvd_acc_head = flt(cum_sum_cvd_acc_head) + flt(r[col_idx['CVD']])
    
    r.append( cum_sum_main_acc_head + cum_sum_add_acc_head + cum_sum_cvd_acc_head)
    cum_sum_edu_cess_acc_head = flt(cum_sum_edu_cess_acc_head) + flt(r[col_idx['Education Cess']])
    r.append(cum_sum_edu_cess_acc_head)
    cum_sum_sh_edu_cess_acc_head = flt(cum_sum_sh_edu_cess_acc_head) + flt(r[col_idx['S.H.Education Cess']])
    r.append(cum_sum_sh_edu_cess_acc_head)
  elif 'CAPITAL' in filter_values['report']:
    # As there is no range and Folio No
    r[col_idx['Baisc Excise Duty']] = r[col_idx['Education Cess']]
    r[col_idx['Additional Duty']] = r[col_idx['S.H.Education Cess']]
    r[col_idx['Education Cess']] = r[col_idx[' Education Cess ']]
    r[col_idx['S.H.Education Cess']] = r[col_idx[' S.H.Education Cess ']]

    cum_sum_main_acc_head = flt(cum_sum_main_acc_head) + flt(r[col_idx['Baisc Excise Duty']]) 
    cum_sum_add_acc_head = flt(cum_sum_add_acc_head) + flt(r[col_idx['Additional Duty']]) 
        
    r[col_idx[' Basic Excise Duty ']]= flt(cum_sum_main_acc_head) + flt(cum_sum_add_acc_head)
    cum_sum_edu_cess_acc_head = flt(cum_sum_edu_cess_acc_head) + flt(r[col_idx['Education Cess']])
    r[col_idx[' Education Cess ']]= flt(cum_sum_edu_cess_acc_head)
    cum_sum_sh_edu_cess_acc_head = flt(cum_sum_sh_edu_cess_acc_head) + flt(r[col_idx['S.H.Education Cess']])
    r[col_idx[' S.H.Education Cess ']]= flt(cum_sum_sh_edu_cess_acc_head)
    
    r.append(0.00)
    r.append(0.00)
    r.append(0.00)
    
    r.append( cum_sum_main_acc_head + cum_sum_add_acc_head)
    r.append(cum_sum_edu_cess_acc_head)
    r.append(cum_sum_sh_edu_cess_acc_head)
  r.append(remarks)


out = []

if 'CAPITAL' not in cstr(filter_values['report']):
  out.append(['Opening Balance of Duty in Credit', '', '', '', '', '', '', '', '', '', '', '','','','', flt(openg_main_acc_head) + flt(openg_add_acc_head) + flt(openg_cvd_acc_head), flt(openg_edu_cess_acc_head), flt(openg_sh_edu_cess_acc_head),''])
elif 'CAPITAL' in filter_values['report']:
  out.append(['Opening Balance of Duty in Credit', '', '', '', '', '', '', '', '', '', '', '', '', '', '', flt(openg_main_acc_head) + flt(openg_add_acc_head) , flt(openg_edu_cess_acc_head), flt(openg_sh_edu_cess_acc_head)])
out += res
#if from_export == 0:
#  msgprint("This is a very large report and cannot be shown in the browser as it is likely to make your browser very slow.Please click on 'Export' to open in a spreadsheet")
#  raise Exception