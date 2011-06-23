if not filter_values.get('based_on'):
  msgprint("Please Select Based On")
  raise Exception
cols, columns = [], []
# Add columns
# ------------
based_on = filter_values.get('based_on').split(NEWLINE)
if len(based_on) == 1:
  if based_on[0] == 'Item Code':
    cols = ["Item Code", "Item Name", "Description", "Stock UOM"]
  elif based_on[0] == 'Warehouse':
    cols = ["Warehouse", "Warehouse Type"]
elif len(based_on) == 2:
  cols = ["Item Code", "Item Name", "Description", "Stock UOM", "Warehouse",  "Warehouse Type"]

for d in cols:
  columns.append([d,'Data','150px',''])

columns.append(['Closing Balance','Currency','200px',''])
columns.append(['Stock Value','Currency','150px',''])

posting_date = filter_values.get('posting_date1')
if not posting_date: posting_date = nowdate()

for c in columns:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1
  
def get_values(msgprint, flt, posting_date, item_code = '', warehouse = ''):
  cl_bal, stock_val = 0,0
  if item_code and not warehouse:
    war_list = sql("select distinct warehouse from `tabStock Ledger Entry` where item_code = %s", item_code)
    for d in war_list:
      act = sql("select bin_aqat, stock_value from `tabStock Ledger Entry` where item_code = %s and warehouse = %s and ifnull(is_cancelled, 'No') = 'No' and timestamp(posting_date, posting_time) <= timestamp(%s, %s) Order by timestamp(posting_date, posting_time) DESC, name DESC LIMIT 1", (item_code, d[0], posting_date, '23:55'))
      cl_bal += act and flt(act[0][0]) or 0.00
      stock_val += act and flt(act[0][1]) or 0.00
  elif warehouse and not item_code:
    item_list = sql("select distinct item_code from `tabStock Ledger Entry` where warehouse = %s", warehouse)
    for d in item_list:
      act = sql("select bin_aqat, stock_value from `tabStock Ledger Entry` where item_code = %s and warehouse = %s and ifnull(is_cancelled, 'No') = 'No' and timestamp(posting_date, posting_time) <= timestamp(%s, %s) Order by timestamp(posting_date, posting_time) DESC, name DESC LIMIT 1", (d[0], warehouse, posting_date, '23:55'))
      cl_bal += act and flt(act[0][0]) or 0.00
      stock_val += act and flt(act[0][1]) or 0.00
  return cl_bal, stock_val

out=[]
cl_bal,tot_stock = 0,0
  
for r in res:
  if len(based_on) == 1:
    if based_on[0] == 'Item Code': closing_balance, stock_value = get_values(msgprint, flt, posting_date, item_code = r[col_idx['Item Code']])
    elif based_on[0] == 'Warehouse': closing_balance, stock_value = get_values(msgprint, flt, posting_date, warehouse = r[col_idx['Warehouse']])
    r.append(closing_balance)
    r.append(stock_value)
  else:
    det = sql("select bin_aqat, stock_value from `tabStock Ledger Entry` where item_code = %s and warehouse = %s and ifnull(is_cancelled, 'No') = 'No' and timestamp(posting_date, posting_time) <= timestamp(%s, %s) Order by timestamp(posting_date, posting_time) DESC, name DESC LIMIT 1", (r[col_idx['Item Code']], r[col_idx['Warehouse']], posting_date, '23:55'))
    
    r.append(det and flt(det[0][0]) or 0.00)
    r.append(det and flt(det[0][1]) or 0.00)
  cl_bal += flt(r[col_idx['Closing Balance']])
  tot_stock += flt(r[col_idx['Stock Value']])
  out.append(r)

# Add the totals row
l_row = ['' for i in range(len(colnames))]
if len(based_on) == 1 and based_on[0] == 'Warehouse':
  l_row[col_idx['Warehouse Type']] = '<b>TOTALS</b>'
else:
  l_row[col_idx['Stock UOM']] = '<b>TOTALS</b>'
l_row[col_idx['Closing Balance']] = cl_bal
l_row[col_idx['Stock Value']] = tot_stock
out.append(l_row)
