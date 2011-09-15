# validate Filters
flt_dict = {'fiscal_year': 'Fiscal Year', 'period': 'Period', 'under' : 'Under', 'based_on' : 'Based On','target_on':'Target On'}
for f in flt_dict:
  if not filter_values.get(f):
    msgprint("Please Select " + cstr(flt_dict[f]))
    raise Exception

# Get Values from fliters
fiscal_year = filter_values.get('fiscal_year')
period = filter_values.get('period')
under = filter_values.get('under')
if under == 'Sales Invoice': under = 'Receivable Voucher'
based_on = filter_values.get('based_on')
target_on = filter_values.get('target_on')

#add distributed id field
col = []
col.append([based_on,'Date','150px',''])
if target_on == 'Quantity':
  col.append(['Target Quantity','Currency','150px',''])
else:
  col.append(['Target Amount','Currency','150px',''])
col.append(['Distribution Id','Date','150px',''])

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  
  col_idx[c[0]] = len(colnames)-1

def make_child_lst(based_on,name):
  rg = sql("select lft, rgt from `tab%s` where name = '%s'"%(based_on,name))
  ch_name = sql("select name from `tab%s` where lft between %d and %d"%(based_on,int(rg[0][0]),int(rg[0][1])))
  chl ='('
  flag = 1
  for c in ch_name:
    if flag == 1:
     chl += "'%s'"%c[0]
     flag = 2
    else:
      chl +=",'%s'"%c[0]

  chl +=")"
  return chl


def get_target(target_on,based_on,fiscal_year,r):

  if target_on == 'Quantity':
    q1 = "select t1.target_qty "
    q2 = "select sum(t1.target_qty)"
  if target_on == 'Amount':
    q1 = "select t1.target_amount "
    q2 = "select sum(t1.target_amount)"
    
  cond1 =" t1.fiscal_year ='%s' and t1.parent=t2.name and t1.parenttype = '%s' and t1.docstatus !=2"
  #----------------------------------------------------------------  
  q = "select t1.name from `tabTarget Detail` t1, `tab%s` t2 where "+cond1+" and t2.name = '%s'"
  ch = sql(q%(based_on,fiscal_year,based_on,r))

  return {'q1':q1,'q2':q2,'cond1':cond1,'ch':ch}

for r in res:
  
  tt = get_target(target_on,based_on,fiscal_year,r[0].strip())
  
  if tt['ch']:
    
    cond2 = " ifnull(t1.item_group,'')='' and"
    qur = tt['q1']+"from `tabTarget Detail` t1, `tab%s` t2 where "+cond2+tt['cond1']+" and t2.name = '%s'"
    ret_amt = sql(qur%(based_on,fiscal_year,based_on,r[0].strip()))
    
    #----------------------------------------------------------------  
    if not ret_amt:
      qur = tt['q2']+"from `tabTarget Detail` t1, `tab%s` t2 where "+tt['cond1']+" and t2.name = '%s'"
      ret_amt = sql(qur%(based_on,fiscal_year,based_on,r[0].strip()))  

  #----------------------------------------------------------------      
  else:
    node_lst = make_child_lst(based_on,r[0].strip())
    qur = tt['q2']+"from `tabTarget Detail` t1, `tab%s` t2 where "+tt['cond1']+" and t2.name in %s"
    ret_amt = sql(qur%(based_on,fiscal_year,based_on,node_lst))    

  #----------------------------------------------------------------  
  ret_dis_id = sql("select distribution_id from `tab%s` where name = '%s'"%(based_on,r[0].strip()))

  target_amt = ret_amt and flt(ret_amt[0][0]) or 0
  dis_id = ret_dis_id and ret_dis_id[0][0] or ''

  r.append(target_amt)
  r.append(dis_id)


# Set required field names 
based_on_fn = (based_on == 'Territory') and 'territory' or 'sales_person'

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
  col = ['Target', 'Actual', 'Variance']
  for c in col:
    n = str(name) and ' (' + str(name) +')' or ''
    colnames.append(str(c) + n)
    coltypes.append('Currency')
    colwidths.append('150px')
    coloptions.append('')
    col_idx[str(c) + n ] = len(colnames) - 1



# make default columns
#coltypes[col_idx[based_on]] = 'Link'
#coloptions[col_idx[based_on]]= based_on

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

  for idx in range(3, len(colnames), 3):
    cidx = 2

    # ================= Calculate Target ==========================================
    r.append(bc_obj.get_monthly_budget( r[cidx], fiscal_year, mon_list[count][data['start_date']], mon_list[count][data['end_date']], r[cidx-1]))
    
    #================== Actual Amount =============================================
    actual = 0

    ch = make_child_lst(based_on,r[0].strip())

    #----------------------------------------------------------    
    if target_on == "Quantity":
      if based_on == "Territory":
        actual = sql("select sum(ifnull(t2.qty,0)) from `tab%s` t1, `tab%s Detail` t2 where t2.parenttype = '%s' and t2.parent = t1.name and t1.%s in %s and t1.docstatus = 1 and t1.%s between '%s' and '%s'" % (under, (under == 'Receivable Voucher') and 'RV' or under, under, based_on_fn, ch, date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
      
      elif based_on == 'Sales Person':
        actual = sql("select sum(ifnull(t2.qty,0) * ifnull(t3.allocated_percentage,0) / 100) from `tab%s` t1, `tab%s Detail` t2, `tabSales Team` t3 where t2.parent = t1.name and t3.parent = t1.name and t3.%s in %s and t1.docstatus != 2 and t1.docstatus = 1 and t1.%s between '%s' and '%s' "%(under, (under == 'Receivable Voucher') and 'RV' or under, based_on_fn, ch, date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
    
    #----------------------------------------------------------  
    if target_on == "Amount":
      if based_on == 'Territory':    
        
        actual = sql("select sum(ifnull(net_total,0)) from `tab%s` where %s in %s and docstatus = 1 and %s between '%s' and '%s' " % (under, based_on_fn, ch, date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
    
      elif based_on == 'Sales Person':
        actual = sql("select sum(ifnull(t2.allocated_amount,0)) from `tab%s` t1, `tabSales Team` t2 where t2.%s in %s and t2.parenttype='%s' and t1.docstatus != 2 and t2.parent = t1.name and t1.%s between '%s' and '%s'"%(under, based_on_fn, ch, under, date_fn, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
    #----------------------------------------------------------
    actual = flt(actual[0][0])
    r.append(actual)
    # ================ Variance ===================================================
    r.append(r[idx] - r[idx + 1])
    count = count +1