col = [['In Store Period (in days)', 'Data', '']]
for c in col:
  colnames.append(str(c[0]))
  coltypes.append(str(c[1]))
  colwidths.append('150px')
  coloptions.append(str(c[2]))
  col_idx[str(c)] = len(colnames) - 1

import datetime
for r in res:
  if r[col_idx['Purchase Date']]:
    dt = (datetime.date.today() - getdate(r[col_idx['Purchase Date']])).days
  else:
    dt = ''
  r.append(dt)