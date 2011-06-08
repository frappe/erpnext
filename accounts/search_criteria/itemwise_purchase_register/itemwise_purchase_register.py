#adding columns

cl = [c[0] for c in sql("select distinct account_head from `tabPurchase Tax Detail` where parenttype='Payable Voucher' and docstatus=1 order by idx asc")]

cl += ['Total Tax', 'Grand Total']
for c in cl:
  colnames.append(c)
  coltypes.append('Currency')
  colwidths.append('100px')
  coloptions.append('')

cl = cl[:-2]
for r in res:
  total_tax = 0
  amt = flt(r[col_idx['Amount (Default Curr.)']] or 0)
  qty = flt(r[col_idx['Qty']] or 0)

  for c in cl:
    val = sql("select t1.tax_amount, t2.net_total from `tabPurchase Tax Detail` t1, `tabPayable Voucher` t2 where t2.name = %s and t1.parent = %s and t1.parenttype='Payable Voucher' and t1.account_head = %s", (r[col_idx['ID']],r[col_idx['ID']], c))
    tax = val and flt(val[0][0]) or 0
    net_total = val and flt(val[0][1]) or 0
    if tax != 0:
      tax = amt*tax/net_total
    total_tax += tax
    
    r.append(tax)
  r.append(total_tax)
  r.append(amt + total_tax)
