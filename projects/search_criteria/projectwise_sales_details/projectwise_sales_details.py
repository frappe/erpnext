based_on = filter_values.get('based_on')

cols=[]

if based_on == 'Sales Order':  
  cols = [['Sales Order No','Link','150px','Sales Order'], ['Order Type','Data','100px',''], ['Status','Data','100px',''], ['Project Name','Link','150px','Project'], ['Customer','Link','150px','Customer'], ['Customer Name','Data','200px',''], ['% Delivered','Currency','100px',''], ['% Billed','Currency','100px',''], ['Grand Total','Currency','150px','']]

elif based_on == 'Delivery Note':
  cols = [['Delivery Note No','Link','150px','Delivery Note'], ['Status','Data','100px',''], ['Project Name','Link','200px','Project'], ['Customer','Link','150px','Customer'], ['Customer Name','Data','200px',''], ['% Installed','Currency','100px',''], ['% Billed','Currency','100px',''], ['Grand Total','Currency','150px','']]

elif based_on == 'Sales Invoice':
  cols = [['Sales Invoice No','Link','150px','Receivable Voucher'], ['Debit To','Data','150px',''], ['Project Name','Link','200px','Project'], ['Customer','Link','150px','Customer'], ['Customer Name','Data','200px',''], ['Grand Total','Currency','150px','']]


for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1