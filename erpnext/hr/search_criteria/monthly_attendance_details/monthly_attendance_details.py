#add column employee, employee name
#--------------------------------------------------------------------------------------
col =[['Employee','Link','155px','Employee'],['Employee Name','Data','150px','']]

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  
  col_idx[c[0]] = len(colnames)-1


#get feb months last day
#--------------------------------------------------------------------------------------
fy = filter_values.get('fiscal_year')
month = filter_values.get('month')
mdict = {'Jan':'01', 'Feb':'02','Mar':'03','Apr':'04','May':'05','June':'06','July':'07','Aug':'08','Sept':'09','Oct':'10','Nov':'11','Dec':'12'}

import webnotes.utils
from dateutil.relativedelta import relativedelta

ysd = sql("select year_start_date from `tabFiscal Year` where name = '%s' and docstatus !=2"%fy)[0][0]

last_date = webnotes.utils.get_last_day(ysd + relativedelta(months = (cint(ysd.strftime('%m'))>cint(mdict[month]) and (12-cint(ysd.strftime('%m'))+cint(mdict[month])) or (cint(mdict[month]) - cint(ysd.strftime('%m'))))))
feb = last_date.strftime('%d')



#get last day and add columns
#--------------------------------------------------------------------------------------
dict = {'Jan': 31,'Feb':cint(feb), 'Mar':31,'Apr':30,'May':31,'June':30,'July':31,'Aug':31,'Sept':30,'Oct':31,'Nov':30,'Dec':31}

for i in range(0,dict[month]):
  colnames.append(i+1)
  coltypes.append('Data')
  colwidths.append('25px')
  
  col_idx[c[0]] = len(colnames)-1
  
#add total present, absent days  
#--------------------------------------------------------------------------------------
tot_col =[['Total Present Days','Data','120px'],['Total Absent Days','Data','120px']]

for c in tot_col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])

  col_idx[c[0]] = len(colnames)-1  
  
#get data
#--------------------------------------------------------------------------------------  


year = last_date.strftime('%Y')
out = []
for r in res:
  p_cnt = a_cnt = 0
  
  for i in range(0,dict[month]):
    new_date = str(year)+'-'+mdict[month]+'-'+((i>=9) and str(i+1) or ('0'+str(i+1)))
    
    chk = sql("select status from `tabAttendance` where employee='%s' and att_date = '%s' and docstatus=1"%(r[0],new_date))
    chk = chk and chk[0][0][0] or '-'
    if chk=='P':
      p_cnt +=1
    elif chk=='A':
      a_cnt +=1
    r.append(chk)

  r.append(p_cnt)
  r.append(a_cnt)

  if p_cnt or a_cnt:
    out.append(r)
