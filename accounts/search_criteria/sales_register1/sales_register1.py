# add additional columns

cl = [c[0] for c in sql("select distinct account_head from `tabRV Tax Detail` where parenttype='Receivable Voucher' and docstatus=1 order by idx asc")]

income_acc = [c[0] for c in sql("select distinct income_account from `tabRV Detail` where parenttype='Receivable Voucher' and docstatus=1 order by idx asc")]

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
  net_total = 0
  for i in income_acc:
    val = sql("select sum(amount) from `tabRV Detail` where parent = %s and parenttype='Receivable Voucher' and income_account = %s", (r[col_idx['ID']], i))
    val = flt(val and val[0][0] or 0)
    net_total += val
    r.append(val)
  r.append(net_total)
  
  total_tax = 0
  for c in cl:
    val = sql("select tax_amount from `tabRV Tax Detail` where parent = %s and parenttype='Receivable Voucher' and account_head = %s", (r[col_idx['ID']], c))
    val = flt(val and val[0][0] or 0)
    total_tax += val
    r.append(val)
  r.append(total_tax)
  r.append(net_total+total_tax)