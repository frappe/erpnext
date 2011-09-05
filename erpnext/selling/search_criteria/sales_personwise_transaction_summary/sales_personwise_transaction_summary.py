if filter_values.get('based_on') == 'Sales Invoice':
  based_on_dt = 'Receivable Voucher'
else:
  based_on_dt = filter_values.get('based_on')

cols = [[filter_values.get('based_on'), 'Link','150px', based_on_dt], ['Customer', 'Link','150px','Customer'], ['Territory', 'Link','120px','Territory'], ['Transaction Date', 'Date', '120px', ''], ['Net Total', 'Currency', '80px', ''], ['Grand Total', 'Currency', '80px', ''], ['Sales Person', 'Link', '150px', 'Sales Person'], ['% Contribution', 'Currency', '120px', ''], ['Contribution Amt', 'Currency', '120px', '']]

for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1
