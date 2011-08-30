# validate Filters
flt_dict = {'fiscal_year': 'Fiscal Year', 'period': 'Period'}
for f in flt_dict:
  if not filter_values.get(f):
    msgprint("Please Select " + cstr(flt_dict[f]))
    raise Exception

# Get Values from fliters
fiscal_year = filter_values.get('fiscal_year')
period = filter_values.get('period')
under = "GL Entry"
based_on = "Cost Center"

#add distributed id field
col = []
col.append([based_on,'Date','150px',''])
col.append(['Budget Allocated','Currency','150px',''])
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



for r in res:
    
  cond1 =" t1.fiscal_year ='%s' and t1.parent=t2.name and t1.parenttype = '%s' and t1.docstatus !=2"
  
  q = "select t1.name from `tabBudget Detail` t1, `tab%s` t2 where "+cond1+" and t2.name = '%s'"
  ch = sql(q%(based_on,fiscal_year,based_on,r[0].strip()))
  q1 = "select sum(t1.budget_allocated) from `tabBudget Detail` t1, `tab%s` t2, `tabAccount` t3 where "
  cond2 = " t3.is_pl_account = 'Yes' and t3.debit_or_credit = 'Debit' and t3.name = t1.account and t1.docstatus != 2 and "
  if ch:
    qur = q1+cond2+cond1+" and t2.name = '%s'"
    ret_amt = sql(qur%(based_on,fiscal_year,based_on,r[0].strip()))
    

  #----------------------------------------------------------------      
  else:
    node_lst = make_child_lst(based_on,r[0].strip())
    qur = q1+cond1+' and '+cond2+" t2.name in %s"

    ret_amt = sql(qur%(based_on,fiscal_year,based_on,node_lst))    

  #----------------------------------------------------------------  
  ret_dis_id = sql("select distribution_id from `tab%s` where name = '%s'"%(based_on,r[0].strip()))

  target_amt = ret_amt and flt(ret_amt[0][0]) or 0
  dis_id = ret_dis_id and ret_dis_id[0][0] or ''

  r.append(target_amt)
  r.append(dis_id)
  


# Set required field names 
based_on_fn = 'cost_center'

date_fn  = 'posting_date' 

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
   
    actual = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1, `tabAccount` t2 where ifnull(t2.is_pl_account, 'No') = 'Yes' and ifnull(t1.is_cancelled, 'No') = 'No' and t1.cost_center in %s and t2.debit_or_credit = 'Debit' and t1.posting_date between '%s' and '%s' and t1.account = t2.name"%(ch, mon_list[count][data['start_date']], mon_list[count][data['end_date']]))
   
    #----------------------------------------------------------
    actual = flt(actual[0][0])
    r.append(actual)
    # ================ Variance ===================================================
    r.append(r[idx] - r[idx + 1])
    count = count +1
