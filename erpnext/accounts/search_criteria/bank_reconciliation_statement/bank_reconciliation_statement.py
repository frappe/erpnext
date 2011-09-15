#get company
company = filter_values.get('company') or get_defaults()['company']

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

opening = get_obj('GL Control').get_as_on_balance(acc_name, fiscal_year, to_date, acc[0][0], acc[0][2], acc[0][3])[2]

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

out.append(['','','','','','<font color = "#000"><b>Balance as per Company Books: </b></font>', opening,'',''])
out.append(['','','','','','<font color = "#000"><b>Amounts not reflected in Bank: </b></font>', total_debit,total_credit,''])
out.append(['','','','','','<font color = "#000"><b>Balance as per Bank: </b></font>', bank_bal,'',''])
