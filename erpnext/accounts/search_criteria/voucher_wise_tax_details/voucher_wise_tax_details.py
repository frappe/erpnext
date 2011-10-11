if filter_values.get('based_on') == 'Sales Invoice':
  based_on_dt = 'Receivable Voucher'
else:
  based_on_dt = filter_values.get('based_on')

cols = [
	[filter_values.get('based_on'), 'Link','150px', based_on_dt],
	['Transaction Date', 'Date', '120px', ''], 
	['Customer', 'Link','150px','Customer'], 
	['Net Total', 'Currency', '80px', ''], 
	['Tax Account', 'Link','150px','Account'], 
	['Description', 'Text','120px',''], 
	['Tax Rate', 'Currency', '80px', ''], 
	['Tax Amount', 'Currency', '80px', '']
]

for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1
