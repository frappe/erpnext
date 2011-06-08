if filter_values.get('period'):
  period_values = filter_values['period']
  if len(period_values.split(NEWLINE))>1:
    msgprint("You can view report only for one period. Please select only one value in period.")
    raise Exception
  else:
    period = period_values.split(NEWLINE)[0]

if filter_values.get('based_on'):
  based_on = filter_values['based_on']
  if len(based_on.split(NEWLINE)) > 1:
    msgprint("You can view report based on only one criteria. Please select only one value in Based On.")
    raise Exception
  else:
    based_on = based_on.split(NEWLINE)[0]

if not filter_values.get('fiscal_year'):
  msgprint("Please Select Fiscal Year")
  raise Exception
elif not filter_values.get('period'):
  msgprint("Please Select Period")
  raise Exception
elif not filter_values.get('based_on'):
  msgprint("Please Select the Criteria on which you want your report to be based")
  raise Exception

fiscal_year = filter_values.get('fiscal_year')

# get fiscal year start date and start month
# ---------------------------------------------------------  
year_start_date = sql("select year_start_date,MONTH(year_start_date) from `tabFiscal Year` where name = %s",fiscal_year)
start_date = year_start_date and year_start_date[0][0] or ''
start_month = year_start_date and year_start_date[0][1] or ''
month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# Add columns based on period
# --------------------------------
columns = []
# ================ Annual ======================
if period == 'Annual':
  columns.append(['Target','Currency','120px',''])
  columns.append(['Actual','Currency','120px',''])

# =========== Half Yearly ======================
elif period == 'Half Yearly':
  columns.append(['Target (H1)','Currency','120px','']) # first half
  columns.append(['Actual (H1)','Currency','120px','']) # first half
  if start_month == 1:  # this is case when fiscal year starts with JAN
    columns.append(['Target (H2)','Currency','120px',''])
    columns.append(['Actual (H2)','Currency','120px',''])
  else:  #this is case when fiscal year starts with other than JAN
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


condition = ' docstatus = 1 and fiscal_year = "'+fiscal_year+'"'


for r in res:
  query = ''

  # ================= Annual Report =============== 
  if period == 'Annual':

    target = sql("select sum(target_amount) from `tabTarget Detail` where parent = %s and parenttype= 'Territory' and fiscal_year = %s ",(r[col_idx['ID']],fiscal_year))
    target = target and flt(target[0][0]) or 0
    r.append(target)

  
    so = sql("select sum(net_total) from `tab%s` where territory = '%s' and %s" % (based_on, r[col_idx['ID']],condition))
    so = so and flt(so[0][0]) or 0
    r.append(so)

  # ================= Half Yearly Report =============== 
  elif period == 'Half Yearly':
    target = sql("select sum(target_amount) from `tabTarget Detail` where parent = %s and parenttype= 'Territory' and fiscal_year = %s",(r[col_idx['ID']],fiscal_year))
    target = target and flt(flt(target[0][0])/2) or 0
    r.append(target)

    query += ' MONTH(transaction_date) BETWEEN '+cstr(start_month)+' and '+cstr(start_month+5)
    so = sql("select sum(net_total) from `tab%s` where territory = '%s'  and %s and %s" % (based_on, r[col_idx['ID']],condition,query))
    so = so and flt(so[0][0]) or 0
    r.append(so)
    
    r.append(target)

    query =''
    query += 'MONTH(transaction_date) NOT BETWEEN '+cstr(start_month)+' and '+cstr(start_month+5)
    so = sql("select sum(net_total) from `tab%s` where territory = '%s'  and %s and %s" % (based_on, r[col_idx['ID']],condition,query))
    so = so and flt(so[0][0]) or 0
    r.append(so)
    query = ''

  # =============== Quarterly Report ==============  
  elif period == 'Quarterly':
    query = ''
    length_1 = (len(month_name) - start_month + 1) / 3; #this gives the total no. of times we need to iterate for quarter
    val = length_1 % 4;
    for i in range(length_1):
      value = 3*i + val;
      query +='SUM(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN net_total ELSE NULL END),'
    length_2 = (start_month - 1) / 3; #this gives the total no. of times we need to iterate for quarter (this is required only if fiscal year starts from april)
    for i in range(length_2):
      query += 'SUM(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN net_total ELSE NULL END)';

    target = sql("select sum(target_amount) from `tabTarget Detail` where parent = %s and parenttype= 'Territory' and fiscal_year = %s",(r[col_idx['ID']],fiscal_year))
    target = target and flt(flt(target[0][0])/4) or 0


    so = sql("SELECT %s from `tab%s` where territory ='%s' and %s " %(query,based_on,r[col_idx['ID']],condition))
    i = 0
    length_l = 0
    for c in columns:
      if length_l == 0:
        r.append(target)
        length_l += 1
      else:
        so_total = so and flt(so[0][i]) or 0
        r.append(so_total)
        i +=1
        length_l = 0

  # ================ Monthly Report =============== 
  elif period == 'Monthly':
    query =''
    target = sql("select sum(target_amount) from `tabTarget Detail` where parent = %s and parenttype= 'Territory' and fiscal_year = %s",(r[col_idx['ID']],fiscal_year))
    #msgprint(target)
    target = target and flt(flt(target[0][0])/12) or 0


    # for loop is required twice coz fiscal year starts from April (this will also work if fiscal year starts in January)
    for i in range(start_month-1,len(month_name)):
      query += 'SUM(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END),'

    for i  in range(start_month-1):
      if i != (start_month-2):
        query += 'SUM(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END),'
      else:
        query += 'SUM(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END)';
    so = sql("SELECT %s from `tab%s` where territory ='%s' and %s " %(query,based_on,r[col_idx['ID']],condition))

    i = 0
    length_l = 0
    for c in columns:
      if length_l == 0:
        r.append(target)
        length_l += 1
      else:
        so_total = so and flt(so[0][i]) or 0
        r.append(so_total)
        i +=1
        length_l = 0