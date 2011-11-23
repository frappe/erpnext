if not filter_values.get('posting_date'):
  msgprint("Enter From Posting Date.")
  raise Exception

if not filter_values.get('posting_date1'):
  msgprint("Enter To Posting Date.")
  raise Exception

if not filter_values.get('company'):
  msgprint("Select Company to proceed.")
  raise Exception



col_list = [['Account', 'Link', '150px', 'Account']
           ,['Total', 'Currency', '150px', '']
           ]
           
for c in col_list:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames) - 1
