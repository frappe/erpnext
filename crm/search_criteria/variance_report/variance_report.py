# Add columns
# -----------
row_list = [['ID','Data','150px','']]

for r in row_list:
  colnames.append(r[0])
  coltypes.append(r[1])
  colwidths.append(r[2])
  coloptions.append(r[3])
  col_idx[r[0]] = len(colnames)-1

if not filter_values.get('fiscal_year'):
  msgprint("Please Select Fiscal Year")
  raise Exception
elif not filter_values.get('period'):
  msgprint("Please Select Period")
  raise Exception
elif not filter_values.get('based_on'):
  msgprint("Please Select the Criteria on which you want your report to be based")
  raise Exception
elif not filter_values.get('group_by') and filter_values.get('item_group'):
  msgprint("Item Group cannot be selected if Group By is not Item Group")
  raise Exception

fiscal_year = filter_values.get('fiscal_year')
period = filter_values.get('period')
based_on = filter_values.get('based_on')
group_by = filter_values.get('group_by')
item_group = filter_values.get('item_group')
msgprint(item_group)
company = filter_values.get('company')
under = filter_values.get('under')

#if filter_values.get('item_group'):
#  itm_grp = filter_values.get('item_group')
  
if based_on == 'Territory':
  based = 'territory'
elif based_on == 'Sales Person':
  based = 'sales_person'
elif based_on == 'Sales Partner':
  based = 'sales_partner'


if under == 'Receivable Voucher':
  under_detail = 'RV'
  dt = 'voucher_date'
else:
  under_detail = under
  dt = "transaction_date"
  
# get fiscal year start date and start month
year_start_date = sql("select year_start_date,MONTH(year_start_date) from `tabFiscal Year` where name = %s",fiscal_year)
start_date = year_start_date and year_start_date[0][0] or ''
start_month = year_start_date and year_start_date[0][1] or ''
month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# Add columns based on period
# --------------------------------
columns = []
if group_by == 'Item Group':
  columns.append(['Item Group','Data','120px',''])
# ================ Annual ======================
if period == 'Annual':
  columns.append(['Target','Currency','120px',''])
  columns.append(['Actual','Currency','120px',''])

# =========== Half Yearly ======================
elif period == 'Half Yearly':
  columns.append(['Target (H1)','Currency','120px','']) # first half
  columns.append(['Actual (H1)','Currency','120px','']) # first half
  columns.append(['Target (H2)','Currency','120px',''])
  columns.append(['Actual (H2)','Currency','120px','']) 
  
# ================ Quarterly ===================
elif period == 'Quarterly':
  length_1 = (len(month_name) - start_month + 1) / 3  #this gives the total no. of times we need to iterate for quarter
  val = length_1 % 4
  q_no = 1
  for i in range(length_1):
    value = 3*i + val
    columns.append(['Target (Q'+cstr(q_no)+')','Currency','120px',''])
    columns.append(['Actual (Q'+cstr(q_no)+')','Currency','120px',''])
    q_no += 1
  length_2 = (start_month - 1) / 3 #this gives the total no. of times we need to iterate for quarter (this is required only if fiscal year starts from april)
  for i in range(length_2):
    columns.append(['Target (Q'+cstr(q_no)+')','Currency','120px',''])
    columns.append(['Actual (Q'+cstr(q_no)+')','Currency','120px',''])
    q_no += 1;

# =============== Monthly ======================
elif period == 'Monthly':
  for i in range(start_month-1,len(month_name)):
    columns.append(['Target ('+month_name[i]+')','Currency','120px',''])
    columns.append(['Actual ('+month_name[i]+')','Currency','120px',''])

  for i  in range(start_month-1):
    columns.append(['Target('+month_name[i]+')','Currency','120px',''])
    columns.append(['Actual ('+month_name[i]+')','Currency','120px',''])

for c in columns:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1

out = []
if company:
  condition = ' fiscal_year = "'+fiscal_year+'" and company = "'+company+'"'
else:
  condition = ' fiscal_year = "'+fiscal_year+'"'

#=================== function for fetching  allocated percentage in Distribution id according to period=============
def get_budget_distribution(period,dist_id,fiscal_year):
  query = ''
  id1 = 1
  if period == 'Half Yearly':
    id2 = 6
    for i in range(2):
      query += 'SUM(CASE WHEN t2.idx BETWEEN '+str(id1)+' AND '+str(id2)+' THEN t2.percentage_allocation ELSE NULL END)'
      id1 += 6
      id2 += 6
      if i < 1 :
        query += ','

  elif period == 'Quarterly':
    id2 = 3
    for i in range(4):
      query += 'SUM(CASE WHEN t2.idx BETWEEN '+str(id1)+' AND '+str(id2)+' THEN t2.percentage_allocation ELSE NULL END)'
      id1 += 3
      id2 += 3
      if i < 3 :
        query += ','
    
  elif period == 'Monthly':
    for i in range(12):
      query += 'SUM(CASE WHEN t2.idx ='+str(id1)+' THEN t2.percentage_allocation ELSE NULL END)'
      id1 += 1
      if i < 11 :
        query += ','
    
#  msgprint(query) 
   
  # Main Query
  dist = sql("select %s from `tabBudget Distribution` t1, `tabBudget Distribution Detail` t2 where t1.name = '%s' and t2.parent = t1.name and t1.fiscal_year = '%s'"%(query,dist_id,fiscal_year))
  dist = dist and dist[0] or 0
#  msgprint(dist)
  bug = []
  for i in dist:
    i = i and float(i) or 0
    bug.append(i)
#  msgprint(bug)
  return bug


#============ function for appending target amt and actual amt in a proper order ======================= 
def appending_func(ran,tl,lst,actual,flt):

  c = 2
  for i in range(ran):
    #==== for each itemgroup their actual amt is appended/inserted between target amt  
    if tl == 0:
      lst.insert(c,actual and flt(actual[0][i]) or 0)
    #======== here actual amt is appended/inserted b/w target amt for a particular territory/sales person/sales partner only if target is not zero 
    elif tl == 1:
#      msgprint(lst)
      lst.insert(c,actual and flt(actual[0][i]) or 0)
    c += 2
  return lst

def get_target(tar_det,group_by,period,fiscal_year,rng,r,get_budget_distribution,flt):

  grp,lst = [],[]
  list_range,tl = 0,0
  if group_by == 'Item Group':
    for i in tar_det:
      if i[0] != '':
        igrp = [i[0]]
        if i[2]:
          dist_id = i[2]
          dist = get_budget_distribution(period,dist_id,fiscal_year)
          for d in dist:
            t = flt(flt(flt(i[1]) * flt(d))/ 100)
            igrp.append(t)            
        else:
          t = i and flt(i[1]/rng) or 0
          for i in range(rng):
            igrp.append(t)
            
        grp.append(igrp)
        list_range +=1
    lst = [1,grp,list_range]
    
    #============== Total target(on basis of whole target ) ============
  else:
    for i in tar_det:
      if i[0] == '':
        if i[2]:
          dist_id = i[2]
          dist = get_budget_distribution(period,dist_id,fiscal_year)
          for d in dist:
            t = flt((flt(i[1]) * flt(d))/ 100)
            r.append(t)
        else:
          tot_target = i and flt(i[1]/rng) or 0
          for i in range(rng):
            r.append(tot_target)
        tl = 1
    lst = [0,r,tl]
  return lst
#============ report display function =====================
for r in res:
  query = ''
  grp=[]
  list_range, count, ap, tot_target, tl = 0,0,0,0,0
    
  #============= ANNUAL REPORT ===================
  if period == 'Annual':
    tar_det = sql("select item_group, target_amount, distribution_id from `tabTarget Detail` where parent = %s and parenttype = %s and fiscal_year = %s",(r[col_idx['ID']],based_on,fiscal_year))
#    msgprint(tar_det)

    #================ Target based on individual item group ==============
    if group_by == 'Item Group':
      for i in tar_det:
        if i[0] != '':
          grp_target = i and flt(i[1]) or 0
          igrp = [i[0],grp_target]
          grp.append(igrp)
#          msgprint(grp)
          list_range +=1
          count = 3

    #============== Total target(will be displayed only if target is specified by the user) ============
    else:
      for i in tar_det:
        # ======= here target is considered and not sum of target of item groups
        if i[0] == '':
          tot_target = tar_det and flt(i[1]) or 0
#          msgprint(tot_target)
    
   #================== Actual Amount =============================================
    if based_on == 'Territory' or based_on == 'Sales Partner':

      if group_by =='Item Group':

        for i in grp:
          item_group = i[0]
          actual = sql("select sum(t2.amount) from `tab%s` t1, `tab%s Detail` t2, `tabItem` t3 where t2.parent = t1.name and t1.%s = '%s' and t3.name = t2.item_code and t3.item_group = '%s' and t1.docstatus = 1 and t1.docstatus != 2 and %s"%(under,under_detail,based,r[col_idx['ID']],item_group,condition))
          msgprint(actual)
          actual = actual and flt(actual[0][0]) or 0
          i.append(actual)
          
      else:
        actual = sql("select sum(net_total) from `tab%s` where %s = '%s' and docstatus = 1 and  %s" % (under, based, r[col_idx['ID']],condition))
        actual = actual and flt(actual[0][0]) or 0
        
    elif based_on == 'Sales Person':
      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select sum(t2.amount) from `tab%s` t1, `tab%s Detail` t2, `tabSales Team` t3, `tabItem` t4 where t2.parent = t1.name and t3.parent = t1.name and t3.%s = '%s' and t4.name = t2.item_code and t4.item_group = '%s' and t1.docstatus != 2 and t1.docstatus = 1 and  %s"%(under,under_detail,based,r[col_idx['ID']],item_group,condition))
          actual = actual and flt(actual[0][0]) or 0
#          msgprint(actual)
          i.append(actual)

      else:
        actual = sql("select sum(t1.net_total) from `tab%s` t1, `tabSales Team` t2 where t2.%s = '%s' and t2.parenttype='%s' and t1.docstatus != 2 and t2.parent = t1.name and %s"%(under,based,r[col_idx['ID']],under,condition))
        actual = actual and flt(actual[0][0]) or 0
#        msgprint(actual)

  # ================= Half Yearly Report =============== 
  elif period == 'Half Yearly':
    tl = 0
    grp_target = []

    tar_det = sql("select item_group, target_amount, distribution_id from `tabTarget Detail` where parent = %s and parenttype = %s and fiscal_year = %s",(r[col_idx['ID']],based_on,fiscal_year)) 
#    msgprint(tar_det)
    
    tar = get_target(tar_det,group_by,period,fiscal_year,2,r,get_budget_distribution,flt)
    if tar[0] == 1:
      grp = tar[1]
      list_range = tar[2]
      count = 5
    else:
      r = tar[1]
      tl = tar[2]
      
    #============= Actual Amount======================
    if group_by == 'Item Group':
      # first half
      query += 'SUM(CASE WHEN MONTH(t1.'+dt+') BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN t2.amount ELSE NULL END),'
      # second half
      query += 'SUM(CASE WHEN MONTH(t1.'+dt+') NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN t2.amount ELSE NULL END)';

    elif based_on != 'Sales Person':
      # first half
      query += 'SUM(CASE WHEN MONTH('+dt+') BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),'
      # second half
      query += 'SUM(CASE WHEN MONTH('+dt+') NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END)';

    else:
      # first half
      query += 'SUM(CASE WHEN MONTH(t1.'+dt+') BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN t1.net_total ELSE NULL END),'
      # second half
      query += 'SUM(CASE WHEN MONTH(t1.'+dt+') NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN t1.net_total ELSE NULL END)';

    #=========== Main Query ===============
    if based_on == 'Territory' or based_on == 'Sales Partner':

      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select %s from `tab%s` t1, `tab%s Detail` t2, `tabItem` t3 where t2.parent = t1.name and t1.%s = '%s' and t3.name = t2.item_code and t3.item_group = '%s' and t1.docstatus = 1 and t1.docstatus != 2 and %s"%(query,under,under_detail,based,r[col_idx['ID']],item_group,condition))
#          msgprint(actual)        
          i = appending_func(2,tl,i,actual,flt)
                    
      else:
        actual = sql("select %s from `tab%s` where %s = '%s' and docstatus = 1 and  %s" % (query,under, based, r[col_idx['ID']],condition))
#        msgprint(actual)

    elif based_on == 'Sales Person':
      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select %s from `tab%s` t1, `tab%s Detail` t2, `tabSales Team` t3, `tabItem` t4 where t2.parent = t1.name and t3.parent = t1.name and t3.%s = '%s' and t4.name = t2.item_code and t4.item_group = '%s' and t1.docstatus != 2 and t1.docstatus = 1 and %s"%(query,under,under_detail,based,r[col_idx['ID']],item_group,condition))
#          msgprint(actual)
          i = appending_func(2,tl,i,actual,flt)
      else:
        actual = sql("select %s from `tab%s` t1, `tabSales Team` t2 where t2.%s = '%s' and t2.parenttype='%s' and t1.docstatus != 2 and t2.parent = t1.name and %s"%(query,under,based,r[col_idx['ID']],under,condition))
#        msgprint(actual)

    if tl == 1:
      r = appending_func(2,tl,r,actual,flt)
#      msgprint(r)

  #============== Quarterly Report =========================
  elif period == 'Quarterly':
    tl = 0
    grp_target = []
    tar_det = sql("select item_group, target_amount, distribution_id from `tabTarget Detail` where parent = %s and parenttype = %s and fiscal_year = %s",(r[col_idx['ID']],based_on,fiscal_year)) 

    tar = get_target(tar_det,group_by,period,fiscal_year,4,r,get_budget_distribution,flt)
    if tar[0] == 1:
      grp = tar[1]
      list_range = tar[2]
      count = 9
    else:
      r = tar[1]
      tl = tar[2]
      
    #======= Actual Amt ==================
    length_1 = (len(month_name) - start_month + 1) / 3; #this gives the total no. of times we need to iterate for quarter
    val = length_1 % 4;
    for i in range(length_1):
      value = 3*i + val;

      if group_by == 'Item Group':
        query += 'SUM(CASE WHEN MONTH(t1.'+dt+') BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN t2.amount ELSE NULL END),'

      elif based_on != 'Sales Person':
        query += 'SUM(CASE WHEN MONTH('+dt+') BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN net_total ELSE NULL END),'

      else:
        query += 'SUM(CASE WHEN MONTH(t1.'+dt+') BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN t1.net_total ELSE NULL END),'

    length_2 = (start_month - 1) / 3; #this gives the total no. of times we need to iterate for quarter (this is required only if fiscal year starts from april)
    for i in range(length_2):
      if group_by == 'Item Group':
        query += 'SUM(CASE WHEN MONTH(t1.'+dt+') BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN t2.amount ELSE NULL END)';

      elif based_on != 'Sales Person':
        query += 'SUM(CASE WHEN MONTH('+dt+') BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN net_total ELSE NULL END)';

      else:
        query += 'SUM(CASE WHEN MONTH(t1.'+dt+') BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN t1.net_total ELSE NULL END)';

    #=========== Main Query ===============
    if based_on == 'Territory' or based_on == 'Sales Partner':

      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select %s from `tab%s` t1, `tab%s Detail` t2, `tabItem` t3 where t2.parent = t1.name and t1.%s = '%s' and t3.name = t2.item_code and t3.item_group = '%s' and t1.docstatus = 1 and t1.docstatus != 2 and %s"%(query,under,under_detail,based,r[col_idx['ID']],item_group,condition))
#          msgprint(actual)
          #================common function          
          i = appending_func(4,tl,i,actual,flt)
          
      else:
        actual = sql("select %s from `tab%s` where %s = '%s' and docstatus = 1 and  %s" % (query,under, based, r[col_idx['ID']],condition))
#        msgprint(actual)
        
    elif based_on == 'Sales Person':
      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select %s from `tab%s` t1, `tab%s Detail` t2, `tabSales Team` t3, `tabItem` t4 where t2.parent = t1.name and t3.parent = t1.name and t3.%s = '%s' and t4.name = t2.item_code and t4.item_group = '%s' and t1.docstatus != 2 and t1.docstatus = 1 and %s"%(query,under,under_detail,based,r[col_idx['ID']],item_group,condition))
#          msgprint(actual)
          i = appending_func(4,tl,i,actual,flt)
      else:
        actual = sql("select %s from `tab%s` t1, `tabSales Team` t2 where t2.%s = '%s' and t2.parenttype='%s' and t1.docstatus != 2 and t2.parent = t1.name and %s"%(query,under,based,r[col_idx['ID']],under,condition))
#        msgprint(actual)

    if tl == 1:
      r = appending_func(4,tl,r,actual,flt)
#      msgprint(r)

  #================ Monthly Report ===========================
  elif period == 'Monthly':
    tl = 0
    grp_target = []
    tar_det = sql("select item_group, target_amount, distribution_id from `tabTarget Detail` where parent = %s and parenttype = %s and fiscal_year = %s",(r[col_idx['ID']],based_on,fiscal_year)) 

    tar = get_target(tar_det,group_by,period,fiscal_year,12,r,get_budget_distribution,flt)
    if tar[0] == 1:
      grp = tar[1]
      list_range = tar[2]
      count = 25
    else:
      r = tar[1]
      tl = tar[2]
      
    #======= Actual Amt ==================
    # for loop is required twice coz fiscal year starts from April (this will also work if fiscal year starts in January)
    for i in range(start_month-1,len(month_name)):
      if group_by == 'Item Group':
        query += 'SUM(CASE WHEN MONTH(t1.'+dt+') = '+cstr(i+1)+' THEN t2.amount ELSE NULL END),'

      elif based_on != 'Sales Person':
        query += 'SUM(CASE WHEN MONTH('+dt+') = '+cstr(i+1)+' THEN net_total ELSE NULL END),'

      else:
        query += 'SUM(CASE WHEN MONTH(t1.'+dt+') = '+cstr(i+1)+' THEN t1.net_total ELSE NULL END),'

    for i  in range(start_month-1):
      if i != (start_month-1):
        if group_by == 'Item Group':
          query += 'SUM(CASE WHEN MONTH(t1.'+dt+') = '+cstr(i+1)+' THEN t2.amount ELSE NULL END)'

        elif based_on != 'Sales Person':
          query += 'SUM(CASE WHEN MONTH('+dt+') = '+cstr(i+1)+' THEN net_total ELSE NULL END)'

        else:
          query += 'SUM(CASE WHEN MONTH(t1.'+dt+') = '+cstr(i+1)+' THEN t1.net_total ELSE NULL END)'

        if i < (start_month -2):
          query += ','

    #=========== Main Query ===============
    if based_on == 'Territory' or based_on == 'Sales Partner':

      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select %s from `tab%s` t1, `tab%s Detail` t2, `tabItem` t3 where t2.parent = t1.name and t1.%s = '%s' and t3.name = t2.item_code and t3.item_group = '%s' and t1.docstatus = 1 and t1.docstatus != 2 and %s"%(query,under,under_detail,based,r[col_idx['ID']],item_group,condition))
#          msgprint(actual)
          #===============common function=====================         
          i = appending_func(12,tl,i,actual,flt)
          
      else:
        actual = sql("select %s from `tab%s` where %s = '%s' and docstatus = 1 and  %s" % (query,under, based, r[col_idx['ID']],condition))
#        msgprint(actual)
        
    elif based_on == 'Sales Person':
      if group_by =='Item Group':
        for i in grp:
          item_group = i[0]
          actual = sql("select %s from `tab%s` t1, `tab%s Detail` t2, `tabSales Team` t3, `tabItem` t4 where t2.parent = t1.name and t3.parent = t1.name and t3.%s = '%s' and t4.name = t2.item_code and t4.item_group = '%s' and t1.docstatus != 2 and t1.docstatus = 1 and %s"%(query,under,under_detail,based,r[col_idx['ID']],item_group,condition))
#          msgprint(actual)
          i = appending_func(12,tl,i,actual,flt)
      else:
        actual = sql("select %s from `tab%s` t1, `tabSales Team` t2 where t2.%s = '%s' and t2.parenttype='%s' and t1.docstatus != 2 and t2.parent = t1.name and %s"%(query,under,based,r[col_idx['ID']],under,condition))
#        msgprint(actual)

    if tl == 1:
      r = appending_func(12,tl,r,actual,flt)
#      msgprint(r)

#-------------DISPLAY OF TARGET vs ACTUAL ON BASIS OF TOTAL TARGET / ITEM GROUP 

  if group_by == 'Item Group':
    for col in range(len(colnames)-1): # this would make all first row blank. just for look
      r.append('')

    for des in range(list_range):
      if ap == 0:
        out.append(r)
        ap = 1
      t_row = ['' for i in range(len(colnames))]

      for v in range(count):
        t_row[col_idx[colnames[v+1]]] = grp[des][v]
#        msgprint(t_row)
      out.append(t_row)

  elif tot_target != 0 and period =='Annual':
    r.append(tot_target)
    r.append(actual)
    out.append(r)
    tot_target = 0

  elif tl == 1:
    out.append(r)