cl = [['Account','Data', '200px'],['Debit/Credit', 'Data', '100px'], ['Group/Ledger', 'Data', '100px'], ['Opening','Data', '100px'],['Closing', 'Data', '100px'],['Inc in Cash','Data','100px']]

for c in cl:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append('')
  col_idx[c[0]] = len(colnames)-1
  

company = filter_values['company']

# transaction date
if not filter_values.get('transaction_date') or not filter_values.get('transaction_date1'):
  msgprint("Please enter From Date and To Date")
  raise Exception
else:
  from_date = add_days(filter_values['transaction_date'], -1)
  to_date = filter_values['transaction_date1']

ysd, fiscal_year = sql("select year_start_date, name from `tabFiscal Year` where %s between year_start_date and date_add(year_start_date,interval 1 year)",from_date)[0]


if from_export == 0 and len(res) >250:
  msgprint("This is very large report and cannot be shown in the browser as it is likely to make your browser very slow. Please click on 'Export' to open in excel")
  raise Exception

total_debit, total_credit, total = 0,0,0
glc = get_obj('GL Control')

for r in res:
  acc = r[col_idx['Account']].strip()
  acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt, group_or_ledger from tabAccount where name = '%s'" % acc)
  r.append(acc_det[0][0])
  r.append(acc_det[0][4])

  opening = glc.get_as_on_balance(acc, fiscal_year, from_date, acc_det[0][0], acc_det[0][2], acc_det[0][3])[2]
  
  amount = sql("select sum(t1.debit), sum(t1.credit) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= '%s' AND t1.posting_date <= '%s' and ifnull(t1.is_opening,'No') = 'No' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s AND is_cancelled = 'No'" % (from_date,to_date, acc_det[0][2], acc_det[0][3]))
  if acc_det[0][0] == 'Debit':
    closing = opening + flt(amount[0][0]) - flt(amount[0][1])
  else:
    closing = opening + flt(amount[0][1]) - flt(amount[0][0])
  
  r.append(fmt_money(flt(opening)))
  r.append(fmt_money(flt(closing)))

  diff = flt(closing) - flt(opening)
  if acc_det[0][0]=='Debit':
    r.append(fmt_money(-diff))
    total -= diff
  else:
    r.append(fmt_money(diff))
    total += diff
  

# net profit
# ------------------

acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt, group_or_ledger from tabAccount where account_name = %s AND company=%s", ('Income',company))
amount = sql("select sum(t1.debit), sum(t1.credit) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= '%s' AND t1.posting_date <= '%s' and ifnull(t1.is_opening,'No') = 'No' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s AND is_cancelled = 'No'" % (from_date,to_date, acc_det[0][2], acc_det[0][3]))
net_income = flt(amount[0][1]) - flt(amount[0][0])

acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt, group_or_ledger from tabAccount where account_name = %s AND company=%s", ('Expenses',company))
amount = sql("select sum(t1.debit), sum(t1.credit) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= '%s' AND t1.posting_date <= '%s' and ifnull(t1.is_opening,'No') = 'No' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s AND is_cancelled = 'No'" % (from_date,to_date, acc_det[0][2], acc_det[0][3]))
net_expenses = flt(amount[0][0]) - flt(amount[0][1])

t_row = ['' for i in range(len(colnames))]
t_row[col_idx['Account']] = 'Net Profit'
t_row[col_idx['Inc in Cash']] = fmt_money(net_income - net_expenses)

total += net_income - net_expenses

res.append(t_row)

# total row
# ------------------
t_row = ['' for i in range(len(colnames))]
t_row[col_idx['Account']] = 'Total Cash Generated'
t_row[col_idx['Inc in Cash']] = fmt_money(total)

res.append(t_row)

# Show Inc / Dec in Bank and Cash Accounts
# ----------------------------------------

t_row = ['' for i in range(len(colnames))]
res.append(t_row)

acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt, group_or_ledger, name from tabAccount where account_type = 'Bank or Cash' AND company=%s AND level=%s", (company, cint(filter_values['level'])))
for acc in acc_det:
  r = [acc[5],]

  opening = glc.get_as_on_balance(acc[5], fiscal_year, from_date, acc[0], acc[2], acc[3])[2]

  amount = sql("select sum(t1.debit), sum(t1.credit) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= '%s' AND t1.posting_date <= '%s' and ifnull(t1.is_opening,'No') = 'No' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s AND is_cancelled = 'No'" % (from_date,to_date, acc[2], acc[3]))
  closing = opening + flt(amount[0][0]) - flt(amount[0][1])
  diff = closing - opening


  r.append(acc_det[0][0])
  r.append(acc_det[0][4])

  r.append(fmt_money(flt(opening)))
  r.append(fmt_money(flt(closing)))

  r.append(fmt_money(diff))

  res.append(r)

