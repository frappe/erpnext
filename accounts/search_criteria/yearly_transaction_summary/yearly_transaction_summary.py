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
if not filter_values.get('from_fiscal_year'):
  msgprint("Please Select From Fiscal Year")
  raise Exception
elif not filter_values.get('to_fiscal_year'):
  msgprint("Please Select To Fiscal Year")
  raise Exception
else:
  from_fiscal_year = filter_values.get('from_fiscal_year')
  to_fiscal_year = filter_values.get('to_fiscal_year')
  company = filter_values.get('company')
  from_date = filter_values.get('date')
  to_date = filter_values.get('date1')
  if from_date != "" and to_date != "":
    get_obj('MIS Control').dates(from_fiscal_year,from_date,to_date) # validate dates (i.e. dates should be between particular fiscal year)
	
# Add columns based on from and to fiscal year---------
columns = []
columns.append(['ID','Data','150px',''])
columns.append(['Description','Data','150px',''])
columns.append([from_fiscal_year,'Data','150px','']) # append from fiscal year column

# === get no. of fiscal years between from and to fiscal year and append columns accordingly ========
start_year = from_fiscal_year.split('-')[1] # eg. from fiscal year 2008-2009 . this gives value 2009
end_year = to_fiscal_year.split('-')[0] # eg. to fiscal year 2009-2010 . this gives value 2009
diff = cint(end_year)-cint(start_year)
if diff > 0:
  year = cint(start_year);
  next_year = 0
  f_year = ''
  for i in range(1,diff+1):
    next_year = cint(year)+1
    f_year = cstr(year)+'-'+cstr(next_year)
    columns.append([f_year,'Data','150px',''])
# ====================================================================================================

columns.append([to_fiscal_year,'Data','150px','']) # append to fiscal year column

for c in columns:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1
  
out = []
# =========================== condition for result ===================================================
if company:
  condition = 'docstatus = 1 and company = "'+company+'"'
else:
  condition = 'docstatus = 1'
  
# ====================================================================================================

for r in res:
  det = ''
  query = ''
  list_range = 0
  if from_date != "" and to_date != "":
    date_1 = cstr(get_obj('MIS Control').dates(from_fiscal_year,from_date,to_date))
    query += 'COUNT(CASE WHEN (fiscal_year = "'+from_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_1.split('~~~')[0]+'" AS DATE) AND CAST("'+date_1.split('~~~')[1]+'" AS DATE))) THEN name ELSE NULL END),SUM(CASE WHEN (fiscal_year = "'+from_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_1.split('~~~')[0]+'" AS DATE) AND CAST("'+date_1.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),MIN(CASE WHEN (fiscal_year = "'+from_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_1.split('~~~')[0]+'" AS DATE) AND CAST("'+date_1.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),MAX(CASE WHEN (fiscal_year = "'+from_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_1.split('~~~')[0]+'" AS DATE) AND CAST("'+date_1.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),AVG(CASE WHEN (fiscal_year = "'+from_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_1.split('~~~')[0]+'" AS DATE) AND CAST("'+date_1.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),'
  else:
    query += 'COUNT(CASE WHEN fiscal_year = "'+from_fiscal_year+'" THEN name ELSE NULL END),SUM(CASE WHEN fiscal_year = "'+from_fiscal_year+'" THEN net_total ELSE NULL END),MIN(CASE WHEN fiscal_year = "'+from_fiscal_year+'" THEN net_total ELSE NULL END),MAX(CASE WHEN fiscal_year = "'+from_fiscal_year+'" THEN net_total ELSE NULL END),AVG(CASE WHEN fiscal_year = "'+from_fiscal_year+'" THEN net_total ELSE NULL END),'
  list_range += 1
	
  if diff > 0:
    year = cint(start_year);
    next_year = 0
    f_year = ''
    for i in range(1,diff+1):
      next_year = cint(year)+1;
      f_year = cstr(year)+'-'+cstr(next_year);
      if from_date != "" and to_date != "":
        date_2 = cstr(get_obj('MIS Control').dates(f_year,from_date,to_date))
        query += 'COUNT(CASE WHEN (fiscal_year = "'+f_year+'" and (transaction_date BETWEEN CAST("'+date_2.split('~~~')[0]+'" AS DATE) AND CAST("'+date_2.split('~~~')[1]+'" AS DATE))) THEN name ELSE NULL END),SUM(CASE WHEN (fiscal_year = "'+f_year+'" and (transaction_date BETWEEN CAST("'+date_2.split('~~~')[0]+'" AS DATE) AND CAST("'+date_2.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),MIN(CASE WHEN (fiscal_year = "'+f_year+'" and (transaction_date BETWEEN CAST("'+date_2.split('~~~')[0]+'" AS DATE) AND CAST("'+date_2.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),MAX(CASE WHEN (fiscal_year = "'+f_year+'" and (transaction_date BETWEEN CAST("'+date_2.split('~~~')[0]+'" AS DATE) AND CAST("'+date_2.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),AVG(CASE WHEN (fiscal_year = "'+f_year+'" and (transaction_date BETWEEN CAST("'+date_2.split('~~~')[0]+'" AS DATE) AND CAST("'+date_2.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),'
      else:
        query += 'COUNT(CASE WHEN fiscal_year = "'+f_year+'" THEN name ELSE NULL END),SUM(CASE WHEN fiscal_year = "'+f_year+'" THEN net_total ELSE NULL END),MIN(CASE WHEN fiscal_year = "'+f_year+'" THEN net_total ELSE NULL END),MAX(CASE WHEN fiscal_year = "'+f_year+'" THEN net_total ELSE NULL END),AVG(CASE WHEN fiscal_year = "'+f_year+'" THEN net_total ELSE NULL END),'
      year += 1
      list_range += 1

  if from_date != "" and to_date != "":
    date_3 = cstr(get_obj('MIS Control').dates(to_fiscal_year,from_date,to_date))
    query += 'COUNT(CASE WHEN (fiscal_year = "'+to_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_3.split('~~~')[0]+'" AS DATE) AND CAST("'+date_3.split('~~~')[1]+'" AS DATE))) THEN name ELSE NULL END),SUM(CASE WHEN (fiscal_year = "'+to_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_3.split('~~~')[0]+'" AS DATE) AND CAST("'+date_3.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),MIN(CASE WHEN (fiscal_year = "'+to_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_3.split('~~~')[0]+'" AS DATE) AND CAST("'+date_3.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),MAX(CASE WHEN (fiscal_year = "'+to_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_3.split('~~~')[0]+'" AS DATE) AND CAST("'+date_3.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END),AVG(CASE WHEN (fiscal_year = "'+to_fiscal_year+'" and (transaction_date BETWEEN CAST("'+date_3.split('~~~')[0]+'" AS DATE) AND CAST("'+date_3.split('~~~')[1]+'" AS DATE))) THEN net_total ELSE NULL END)'
  else:
    query += 'COUNT(CASE WHEN fiscal_year = "'+to_fiscal_year+'" THEN name ELSE NULL END),SUM(CASE WHEN fiscal_year = "'+to_fiscal_year+'" THEN net_total ELSE NULL END),MIN(CASE WHEN fiscal_year = "'+to_fiscal_year+'" THEN net_total ELSE NULL END),MAX(CASE WHEN fiscal_year = "'+to_fiscal_year+'" THEN net_total ELSE NULL END),AVG(CASE WHEN fiscal_year = "'+to_fiscal_year+'" THEN net_total ELSE NULL END)'
  list_range += 1
  
  # Main Query
  det = sql("SELECT %s from `tab%s` where %s" %(query,r[col_idx['ID']],condition))
  
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