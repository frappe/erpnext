out=[]
qty,amt,bil_qty=0,0,0

for r in res:
  qty += flt(r[col_idx['Quantity']])
  amt += flt(r[col_idx['Amount*']])
  bil_qty += flt(r[col_idx['Billed Qty']])
  out.append(r)


#Add the totals row
l_row = ['' for i in range(len(colnames))]
l_row[col_idx['Item Name']] = '<b>TOTALS</b>'
l_row[col_idx['Quantity']] = qty
l_row[col_idx['Amount*']] = amt
l_row[col_idx['Billed Qty']] = bil_qty
out.append(l_row)