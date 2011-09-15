if not filter_values.get('posting_date'):
  msgprint("Enter From Posting Date.")
  raise Exception

if not filter_values.get('posting_date1'):
  msgprint("Enter To Posting Date.")
  raise Exception

if not filter_values.get('company'):
  msgprint("Select Comapny.")
  raise Exception


#for r in res:
#  par_acc = sql("SELECT parent.name FROM `tabAccount` AS node,`tabAccount` AS parent WHERE node.lft BETWEEN parent.lft AND parent.rgt AND node.name = '%s' and parent.cash_flow_level = 'Yes' ORDER BY parent.lft DESC"% r[0])
#  r.append(par_acc and par_acc[0][0] or '')

col_list = [['Account', 'Link', '150px', 'Account']
           ,['Total', 'Currency', '150px', '']
#           ,['Parent Account', 'Link', '150px', 'Account']
           ]
for c in col_list:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames) - 1