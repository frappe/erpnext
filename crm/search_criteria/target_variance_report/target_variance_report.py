# validate Filters
flt_dict = {'fiscal_year': 'Fiscal Year', 'period': 'Period', 'company':'Company', 'under' : 'Under', 'based_on' : 'Based On'}
for f in flt_dict:
  if not filter_values.get(f):
    msgprint("Please Select " + cstr(flt_dict[f]))
    raise Exception

# Get Values from fliters
fiscal_year = filter_values.get('fiscal_year')
period = filter_values.get('period')
under = filter_values.get('under')
based_on = filter_values.get('based_on')
group_by = filter_values.get('group_by')

# Set required field names 
based_on_fn = (based_on == 'Cost Center') and 'cost_center' or (based_on == 'Sales Partner') and 'sales_partner' or (based_on == 'Sales Person') and 'sales_person'
date_fn  = (under == 'Sales Order' ) and 'transaction_date' or 'posting_date' 

mon_list = []
data = {'start_date':0, 'end_date':1}

def make_month_list(append_colnames, start_date, mon_list, period, colnames, coltypes, colwidths, coloptions, col_idx):
  count = 1
  if period == 'Quarterly' or period == 'Half Yearly' or period == 'Annual': mon_list.append([str(start_date)])
  for m in range(12):
    # get last date
    last_date = str(sql("select LAST_DAY('%s')" % start_date)[0][0])
    
    # make mon_list for Monthly Period
    if period == 'Monthly' :
      mon_list.append([start_date, last_date])
      # add months as Column names
      month_name = sql("select MONTHNAME('%s')" % start_date)[0][0]
      append_colnames(str(month_name)[:3], colnames, coltypes, colwidths, coloptions, col_idx)
      
    # get start date
    start_date = str(sql("select DATE_ADD('%s',INTERVAL 1 DAY)" % last_date)[0][0])
    
    # make mon_list for Quaterly Period
    if period == 'Quarterly' and count % 3 == 0: 
      mon_list[len(mon_list) - 1 ].append(last_date)
      # add Column names
      append_colnames('Q '+ str(count / 3), colnames, coltypes, colwidths, coloptions, col_idx)
      if count != 12: mon_list.append([start_date])
    
    # make mon_list for Half Yearly Period
    if period == 'Half Yearly' and count % 6 == 0 :
      mon_list[len(mon_list) - 1 ].append(last_date)
      # add Column Names
      append_colnames('H'+str(count / 6), colnames, coltypes, colwidths, coloptions, col_idx)
      if count != 12: mon_list.append([start_date])

    # make mon_list for Annual Period
    if period == 'Annual' and count % 12 == 0:
      mon_list[len(mon_list) - 1 ].append(last_date)
      # add Column Names
      append_colnames('', colnames, coltypes, colwidths, coloptions, col_idx)
    count = count +1

def append_colnames(name, colnames, coltypes, colwidths, coloptions, col_idx):
  col = ['Budget', 'Actual', 'Variance']
  for c in col:
    colnames.append(str(c) + ' (' + str(name) +')' )
    coltypes.append('Currency')
    colwidths.append('150px')
    coloptions.append('')
    col_idx[str(c) + ' (' + str(name) +')' ] = len(colnames) - 1

# make default columns
coltypes[col_idx[based_on]] = 'Link'
coloptions[col_idx[based_on]]= based_on 

# get start date
start_date = get_value('Fiscal Year', fiscal_year, 'year_start_date')
if not start_date:
  msgprint("Please Define Year Start Date for Fiscal Year " + str(fiscal_year))
  raise Exception
start_date = start_date.strftime('%Y-%m-%d')

# make month list and columns
make_month_list(append_colnames, start_date, mon_list, period, colnames, coltypes, colwidths, coloptions, col_idx)

bc_obj = get_obj('Budget Control')
for r in res:
  count = 0
  for idx in range((group_by == 'Item Group') and 4 or 3, len(colnames), 3):
    cidx = (group_by == 'Item Group') and 3 or 2
    # ================= Calculate Target ==========================================
    r.append(bc_obj.get_monthly_budget( r[cidx], fiscal_year, mon_list[count][data['start_date']], mon_list[count][data['end_date']], r[cidx-1]))
    
    #================== Actual Amount =============================================
    actual = 0
    if based_on == 'Cost Center' or based_on == 'Sales Partner':
      if group_by =='Item Group':
        actual = sql("select sum(ifnull(t2.amount,0)) from `tab%s` t1, `tab%s Detail` t2, `tabItem` t3 where t2.parenttype = '%s' and t2.parent = t1.name and t1.%s = '%s' and t3.name = t2.item_code and t3.item_group = '%s' and t1.docstatus = 1 and t1.%s between '%s' and '%s'" % (under, (under == 'Receivable Voucher') and 'RV' or under, under, based_on_fn, r[0], r[1], date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
        actual = flt(actual[0][0])
      else:
        actual = sql("select sum(ifnull(net_total,0)) from `tab%s` where %s = '%s' and docstatus = 1 and %s between '%s' and '%s' " % (under, based_on_fn, r[0], date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
        actual = flt(actual[0][0])
    elif based_on == 'Sales Person':
      if group_by =='Item Group':
        actual = sql("select sum(ifnull(t2.amount,0) * ifnull(t3.allocated_percentage,0) / 100) from `tab%s` t1, `tab%s Detail` t2, `tabSales Team` t3, `tabItem` t4 where t2.parent = t1.name and t3.parent = t1.name and t3.%s = '%s' and t4.name = t2.item_code and t4.item_group = '%s' and t1.docstatus != 2 and t1.docstatus = 1 and t1.%s between '%s' and '%s' "%(under, (under == 'Receivable Voucher') and 'RV' or under, based_on_fn, r[0], r[1], date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
        actual = flt(actual[0][0])
      else:
        actual = sql("select sum(ifnull(t2.allocated_amount,0)) from `tab%s` t1, `tabSales Team` t2 where t2.%s = '%s' and t2.parenttype='%s' and t1.docstatus != 2 and t2.parent = t1.name and t1.%s between '%s' and '%s'"%(under, based_on_fn, r[0], under, date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
        actual = flt(actual[0][0])
    r.append(actual)
    # ================ Variance ===================================================
    r.append(r[idx] - r[idx + 1])
    count = count +1