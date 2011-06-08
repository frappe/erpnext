total = 0.0
monthlist = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
for r in res:
  r[0] = monthlist[r[0]]
  total += r[1]

colwidths[col_idx['Total Despatched']] = '200px'