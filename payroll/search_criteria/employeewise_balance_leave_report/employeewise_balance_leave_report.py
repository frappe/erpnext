leave_types = sql("select name from `tabLeave Type` where docstatus != 2 and name not in ('Compensatory Off','Leave Without Pay')")
msgprint(leave_types)
col=[]
  
for e in leave_types:
  l = (len(e)*9) 
  if l < 150 : col_width = '150px'
  else:  col_width = '%spx'%(l)
  
  col.append([e,'Currency',col_width,''])


col.append(['Total Balance','Currency','150px',''])

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)
