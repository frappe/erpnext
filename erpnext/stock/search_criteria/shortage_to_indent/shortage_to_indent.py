mon_list = []
data = {'start_date':0, 'end_date':1, 'working_days': 2}

def make_month_list(start_date, end_date, mon_list, colnames, coltypes, colwidths, coloptions, col_idx):

  # get period between from date and to date

  period_diff = sql("select PERIOD_DIFF('%s','%s')"% (('').join( end_date.split('-')[i] for i in range(len(end_date.split('-')) - 1)),('').join(start_date.split('-')[i] for i in range(len(start_date.split('-')) - 1))))
  period_diff = period_diff and int(period_diff[0][0])

  for pd in range(int(period_diff) + 1):
    # get last date
    last_date = str(sql("select LAST_DAY('%s')" % start_date)[0][0])
      
    # get no of days in the month            
    if not int(sql("select DATEDIFF('%s','%s')" % (end_date, last_date))[0][0]) >0:
      last_date = end_date
    diff = int(sql("select DATEDIFF('%s','%s')" % (last_date, start_date))[0][0]) + 1
      
    # make mon_list
    mon_list.append([start_date, last_date, (diff > 26) and 26 or diff])
           
    # add months as Column names
    month_name = sql("select MONTHNAME('%s')" % start_date)[0][0]
  
    colnames.append(str(str(month_name)[:3])+ '-'+ str(start_date[:4]))
    coltypes.append('Currency')
    colwidths.append('150px')
    coloptions.append('')
    col_idx[str(str(month_name)[:3])+ '-'+ str(start_date[:4])] = len(colnames) - 1

    # get start date
    start_date = str(sql("select DATE_ADD('%s',INTERVAL 1 DAY)" % last_date)[0][0])

# Validation for 'ID' and 'Lead Time Days' Column Name
if 'ID' not in colnames or 'Lead Time Days' not in colnames:
  msgprint("Please select Id and Lead Time Days in 'Select Columns' tab Else Report will not be generated")
  raise Exception

# Validation for Posting Date Filters
if not filter_values.get('posting_date') or not filter_values.get('posting_date1'):
  msgprint("Please select From Posting Date and To Posting Date")
  raise Exception
else:
  from_date = str(filter_values.get('posting_date'))
  to_date = str(filter_values.get('posting_date1'))


# Call Make Month List Function
make_month_list(from_date, to_date, mon_list, colnames, coltypes, colwidths, coloptions, col_idx)


# Add Column names 
col = [['Total Daily Consumption','Currency','150px','']
      ,['MIL(Min Inv. Level)','Currency','150px','']
      ,['ROL(Re-Order Level)','Currency','150px','']
      ,['Actual Quantity','Currency','150px','']
      ,['Indented Quantity','Currency','150px','']
      ,['Ordered Quantity','Currency','150px','']
      ,['Shortage To Indent','Currency','150px','']
      ,['MAR','Currency','100px','']
      ,['LPR','Currency','100px','']]

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames) - 1

for r in res:

  # calculate Total Daily Consumption Monthly
  count, tot_consumption, tot_days = 0, 0, 1
  #for idx in range(col_idx['Stock Unit of Measurement'] + 1 , col_idx['Total Daily Consumption'] ):
  for idx in range(col_idx['Lead Time Days'] + 1 , col_idx['Total Daily Consumption'] ):
  
    # As Consumption Means:= Adding Qty Transfered to WIP Warehouse ++ Qty Issued directly warehouse whose waraehouse_type != WIP Warehouse and Subtracting Qty Issued from WIP Warehouse
    #Capture item qty coming to WIP Warehouse for production purpose which means consuming that items
    add_con = sql("select ifnull(sum(t1.actual_qty),0)  from `tabStock Ledger Entry` t1 where t1.item_code = '%s' and t1.is_cancelled = 'No'  and t1.posting_date >= '%s' and t1.posting_date <= '%s' and t1.warehouse_type = 'WIP Warehouse' and t1.actual_qty > 0 " % (r[col_idx['ID']],mon_list[count][data['start_date']],mon_list[count][data['end_date']]))
    
    # This is Stock Entry which is of Type Material Issue also to mention that Source Warehouse should not be WIP WArehouse
    #Transfering items to Internal Other Warehouse but not to WIP Warehouse
    dir_con = sql("select ifnull(sum(t1.actual_qty),0) from `tabStock Ledger Entry` t1, `tabStock Entry Detail` t2 where t1.item_code = '%s' and t1.is_cancelled = 'No' and t1.posting_date >= '%s' and t1.posting_date <= '%s' and t1.warehouse_type != 'WIP Warehouse' and t1.actual_qty < 0 and t1.voucher_type = 'Stock Entry' and t1.voucher_detail_no = t2.name and ifnull(t2.t_warehouse, '') = ''"%(r[col_idx['ID']],mon_list[count][data['start_date']],mon_list[count][data['end_date']]))
    
    # This is Stock Entry which is of Type MAterial TRansfer also to mention that Source Warehouse should be WIP WArhouse
    #like, transfering items from internal warehouse to customer
    red_con = sql("select ifnull(sum(t1.actual_qty),0) from `tabStock Ledger Entry` t1, `tabStock Entry Detail` t2 where t1.item_code = '%s' and t1.is_cancelled = 'No'  and t1.posting_date >= '%s' and t1.posting_date <= '%s' and t1.warehouse_type = 'WIP Warehouse' and t1.actual_qty < 0 and t1.voucher_type = 'Stock Entry' and t1.voucher_detail_no = t2.name and ifnull(t2.t_warehouse, '') != ''"%(r[col_idx['ID']],mon_list[count][data['start_date']],mon_list[count][data['end_date']]))
    #msgprint(str(add_con[0][0]) + "~~~" + str(dir_con[0][0]) + "~~~" + str(red_con[0][0]))

    add_con = add_con and add_con[0][0] or 0.00
    dir_con = dir_con and ((-1) * dir_con[0][0]) or 0.00
    red_con = red_con and red_con[0][0] or 0.00
    tot_con = flt(add_con) + flt(dir_con) + flt(red_con)
    #tot_con = add_con and add_con[0][0] or 0 + dir_con and (-1) * dir_con[0][0] or 0 +  red_con and red_con[0][0] or 0
    tot_con = flt(r[col_idx['Lead Time Days']] and tot_con  or 0)


    # monthly avg consumption
    r.append(flt(tot_con / mon_list[count][data['working_days']]))

    # calculate tot_consumption and tot_days   
    tot_consumption = flt(tot_consumption) + flt(tot_con)
    tot_days = (tot_days == 1) and flt(mon_list[count][data['working_days']]) or (flt(tot_days) + flt(mon_list[count][data['working_days']]))
    count = count + 1  

  # Calculate Daily Consumption
  r.append(tot_consumption and flt(tot_consumption /tot_days) or 0)

  # Calculate Minimum Inventory Level
  r.append(flt(r[col_idx['Total Daily Consumption']]) * flt(r[col_idx['Lead Time Days']]))
 
  # Calculate Re-Order Level
  r.append(flt(r[col_idx['MIL(Min Inv. Level)']] * 2))

  # get stock level
  stock_level = sql("select sum(t1.actual_qty), sum(t1.indented_qty), sum(t1.ordered_qty) from `tabBin` t1, `tabWarehouse` t2 where t1.warehouse = t2.name and t2.warehouse_type != 'WIP Warehouse' and t1.item_code = '%s'"%(r[col_idx['ID']]))
 
  r.append(stock_level and flt(stock_level[0][0]) or 0) # Actual Qty
  r.append(stock_level and flt(stock_level[0][1]) or 0) # Indented Qty
  r.append(stock_level and flt(stock_level[0][2]) or 0) # Ordered Qty
  
  # calculate shortage
  r.append((r[col_idx['ROL(Re-Order Level)']] > 0) and flt(flt(r[col_idx['ROL(Re-Order Level)']]) - flt(r[col_idx['Actual Quantity']]) - flt(r[col_idx['Indented Quantity']]) - flt(r[col_idx['Ordered Quantity']])) or 0)

  # get moving average rate
  m_a_r = sql("select ifnull(sum(t1.ma_rate), 0)/ ifnull(count(t1.name),1) from `tabBin` t1, `tabWarehouse` t2 where t1.item_code = '%s' and ifnull(t1.ma_rate, 0) > 0 and t1.warehouse = t2.name and t2.warehouse_type != 'WIP Warehouse'" % r[col_idx['ID']])
  r.append(m_a_r and flt(m_a_r[0][0]) or 0)
    
  # get recent last purchase rate 
  lpr_rate = flt(sql("select last_purchase_rate from `tabItem` where name = '%s'" %r[col_idx['ID']])[0][0]) or 0.00
  r.append(lpr_rate)
