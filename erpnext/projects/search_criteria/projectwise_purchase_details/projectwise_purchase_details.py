based_on = filter_values.get('based_on')
# make default columns
#for r in res:
col = []
if based_on == 'Purchase Order':
  col = [['Purchase Order ID','Link','Purchase Order'],['Status','Data',''],['Project Name','Link','Project'],['Supplier','Link','Supplier'],['Supplier Name','Data',''],['% Received','Data',''],['% Billed','Data',''],['Grand Total','Currency','']] 

elif based_on == 'Purchase Invoice':
  col = [['Purchase Receipt ID','Link','Payable Voucher'],['Status','Data',''],['Project Name','Link','Project'],['Supplier','Link','Supplier'],['Supplier Name','Data',''],['Grand Total','Currency','']]

elif based_on == 'Purchase Receipt':
  col = [['Purchase Invoice ID','Link','Purchase Receipt'],['Credit To','Data',''],['Project Name','Link','Project'],['Supplier','Link','Supplier'],['Supplier Name','Data',''],['Grand Total','Currency','']]
 
  
for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  coloptions.append(c[2])
  l = (len(c[0])*9) 
  if l < 150 : col_width = '150px'
  else:  col_width = '%spx'%(l)
  colwidths.append(col_width)
  col_idx[c[0]] = len(colnames)-1  