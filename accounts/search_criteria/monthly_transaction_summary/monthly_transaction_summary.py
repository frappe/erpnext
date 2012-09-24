# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
if filter_values.get('period'):
  period_values = filter_values.get('period').split(NEWLINE)

if not filter_values.get('fiscal_year'):
  msgprint("Please Select Fiscal Year")
  raise Exception
elif not filter_values.get('period'):
  msgprint("Please Select Period")
  raise Exception
elif len(period_values) > 2:
  msgprint("You can view report only for one period. Please select only one value in period.")
  raise Exception
else:
  fiscal_year = filter_values.get('fiscal_year')
  period = filter_values.get('period')
  company = filter_values.get('company')

# get fiscal year start date and start month
# ---------------------------------------------------------  
year_start_date = sql("select year_start_date,MONTH(year_start_date) from `tabFiscal Year` where name = %s",fiscal_year)
start_date = year_start_date and year_start_date[0][0] or ''
start_month = year_start_date and year_start_date[0][1] or ''
month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# Add columns based on period
# --------------------------------
columns = []
columns.append(['ID','Data','150px',''])
columns.append(['Description','Data','150px',''])
# ================ Annual ======================
if period == 'Annual':
  columns.append([fiscal_year,'Currency','150px',''])
  
# =========== Half Yearly ======================
elif period == 'Half Yearly':
  columns.append([month_name[start_month-1]+' to '+month_name[start_month+4],'Currency','150px','']) # first half
  if start_month == 1:  # this is case when fiscal year starts with JAN
    columns.append([month_name[start_month+5]+' to '+month_name[start_month+11],'Currency','150px',''])
  else:  #this is case when fiscal year starts with other than JAN
    columns.append([month_name[start_month+5]+' to '+month_name[start_month-2],'Currency','150px',''])
  columns.append(['Total','Currency','150px',''])
  
# ================ Quarterly ===================
elif period == 'Quarterly':
  length_1 = (len(month_name) - start_month + 1) / 3  #this gives the total no. of times we need to iterate for quarter
  val = length_1 % 4
  q_no = 1
  for i in range(length_1):
    value = 3*i + val
    columns.append(['Q'+cstr(q_no)+' ('+month_name[value]+' to '+month_name[value+2]+')','Currency','150px',''])
    q_no += 1
  length_2 = (start_month - 1) / 3 #this gives the total no. of times we need to iterate for quarter (this is required only if fiscal year starts from april)
  for i in range(length_2):
    columns.append(['Q'+cstr(q_no)+' ('+month_name[3*i]+' to '+month_name[3*i+2]+')','Currency','150px',''])
    q_no += 1;
  columns.append(['Total','Currency','150px',''])
  
# =============== Monthly ======================
elif period == 'Monthly':
  for i in range(start_month-1,len(month_name)):
    columns.append([month_name[i],'Currency','150px',''])
  for i  in range(start_month-1):
    columns.append([month_name[i],'Currency','150px',''])
  columns.append(['Total','Currency','150px',''])

for c in columns:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1

out = []
if company:
  condition = 'docstatus = 1 and fiscal_year = "'+fiscal_year+'" and company = "'+company+'"'
else:
  condition = 'docstatus = 1 and fiscal_year = "'+fiscal_year+'"'

for r in res:
  det = ''
  list_range = 0
  query = ''
  # ================= Annual Report =============== 
  if period == 'Annual':
    # Main Query
    det = sql("SELECT count(*), SUM(net_total), MIN(net_total), MAX(net_total), AVG(net_total) from `tab%s` where %s" %(r[col_idx['ID']],condition))
    list_range = 1
    
  # ============ Half Yearly Report ===============
  elif period == 'Half Yearly':
    # first half
    query += 'COUNT(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN name ELSE NULL END),SUM(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),MIN(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),MAX(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),AVG(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),'
    # second half
    query += 'COUNT(CASE WHEN MONTH(transaction_date) NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN name ELSE NULL END),SUM(CASE WHEN MONTH(transaction_date) NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),MIN(CASE WHEN MONTH(transaction_date) NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),MAX(CASE WHEN MONTH(transaction_date) NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),AVG(CASE WHEN MONTH(transaction_date) NOT BETWEEN '+cstr(start_month)+' AND '+cstr(start_month+5)+' THEN net_total ELSE NULL END),'
    
    # Main Query
    det = sql("SELECT %s count(*), SUM(net_total), MIN(net_total), MAX(net_total), AVG(net_total) from `tab%s` where %s and transaction_date > CAST('%s' AS DATE)" %(query,r[col_idx['ID']],condition,start_date))
    list_range = 3

  # =============== Quarterly Report ==============  
  elif period == 'Quarterly':
    length_1 = (len(month_name) - start_month + 1) / 3; #this gives the total no. of times we need to iterate for quarter
    val = length_1 % 4;
    for i in range(length_1):
      value = 3*i + val;
      query += 'COUNT(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN name ELSE NULL END),SUM(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN net_total ELSE NULL END),MIN(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN net_total ELSE NULL END),MAX(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN net_total ELSE NULL END),AVG(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(value+1)+' AND '+cstr(value+3)+' THEN net_total ELSE NULL END),'
    length_2 = (start_month - 1) / 3; #this gives the total no. of times we need to iterate for quarter (this is required only if fiscal year starts from april)
    for i in range(length_2):
      query += 'COUNT(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN name ELSE NULL END),SUM(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN net_total ELSE NULL END),MIN(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN net_total ELSE NULL END),MAX(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN net_total ELSE NULL END),AVG(CASE WHEN MONTH(transaction_date) BETWEEN '+cstr(3*i+1)+' AND '+cstr(3*i+3)+' THEN net_total ELSE NULL END),';  
    # Main Query
    det = sql("SELECT %s count(*), SUM(net_total), MIN(net_total), MAX(net_total), AVG(net_total) from `tab%s` where %s and transaction_date > CAST('%s' AS DATE)" %(query,r[col_idx['ID']],condition,start_date))
    list_range = 5
    
  # ================ Monthly Report =============== 
  elif period == 'Monthly':
    # for loop is required twice coz fiscal year starts from April (this will also work if fiscal year starts in January)
    for i in range(start_month-1,len(month_name)):
      query += 'COUNT(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN name ELSE NULL END), SUM(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END),MIN(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END), MAX(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END), AVG(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END),'
      # the above query calculates total_no, total_amt, min_amt, max_amt, avg_amt of doctypes in monthwise
    for i  in range(start_month-1):
      query += 'COUNT(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN name ELSE NULL END), SUM(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END),MIN(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END), MAX(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END), AVG(CASE WHEN MONTH(transaction_date) = '+cstr(i+1)+' THEN net_total ELSE NULL END),'
    
    # Main Query
    det = sql("SELECT %s count(*), SUM(net_total), MIN(net_total), MAX(net_total), AVG(net_total) from `tab%s` where %s and transaction_date > CAST('%s' AS DATE)" %(query,r[col_idx['ID']],condition,start_date))
    list_range = 13
  
  # bifurcate all values and append them in list
  total_no,total_amt,min_amt,max_amt,avg_amt = [],[],[],[],[]
  
  count = 0
  # append values to list
  for i in range(list_range):
    total_no.append(cstr(det and det[0][count] or 0))
    total_amt.append(cstr(det and det[0][count+1] or 0))
    min_amt.append(cstr(det and det[0][count+2] or 0))
    max_amt.append(cstr(det and det[0][count+3] or 0))
    avg_amt.append(cstr(det and det[0][count+4] or 0))
    count += 5
    
  for col in range(len(colnames)-1): # this would make all first row blank. just for look
    r.append('')
  out.append(r)
  
  d = [['Total No',total_no],['Total Amount',total_amt],['Min Amount',min_amt],['Max Amount',max_amt],['Avg Amount',avg_amt]]
  
  for des in range(5):
    t_row = ['' for i in range(len(colnames))]
    t_row[col_idx['Description']] = d[des][0]
    for v in range(list_range):
      t_row[col_idx[colnames[v+2]]] = flt(d[des][1][v])
    out.append(t_row)