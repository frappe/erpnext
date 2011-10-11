for c in range(0,len(colnames)):
  l = (len(colnames[c])*9) 
  if l < 150 : col_width = '150px'
  else:  col_width = '%spx'%(l)

  colwidths[c] = col_width