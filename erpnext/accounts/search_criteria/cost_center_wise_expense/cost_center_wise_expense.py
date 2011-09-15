# Add columns
# -----------
row_list = [['Cost Center','Data','160px'],
            ['Account','Data','160px'],
            ['Debit','Data','120px'],
            ['Credit','Data','120px'], 
            ['Expense','Currency','120px']]  

for r in row_list:
  colnames.append(r[0])
  coltypes.append(r[1])
  colwidths.append(r[2])
  col_idx[r[0]] = len(colnames)-1