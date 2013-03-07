from __future__ import unicode_literals
colwidths[col_idx['Employee Name']]="120px" 
colwidths[col_idx['Leave Without Pay']] = '120px'

sum_net = total_earning = total_deduction = total_lwp = total_arr = 0
total = ['Total Net Pay','','']


earn_type_lst = sql("select name from `tabEarning Type`")

ded_type_lst = sql("select name from `tabDeduction Type`")
li=[]
for lst in earn_type_lst:
  
  li.append(lst[0])
  
  

li.append('Total Earning')
for lst in ded_type_lst:
  
  li.append(lst[0])
  

li.append('Total Deduction')
li.append('Net Pay')



for d in li:
  colnames.append(d)
  colwidths.append("150px")
  coltypes.append("Currency")
  coloptions.append("")
  col_idx[d] = len(colnames)-1
  for r in res:
    r.append("0")

for r in res:
  
  total_lwp += flt(r[col_idx['Leave Without Pay']])
  total_arr += flt(r[col_idx['Arrear Amount']])
  
  for d1 in li:
    d2 = '%s'%d1
    
    earn_ret=webnotes.conn.convert_to_lists(sql("select e_type,e_amount from `tabSalary Slip Earning` where parent = '%s'"%r[col_idx['ID']]))
    ded_ret=webnotes.conn.convert_to_lists(sql("select d_type,d_amount from `tabSalary Slip Deduction` where parent = '%s'"%r[col_idx['ID']]))
    

    for e in earn_ret:
      e0 = '%s'%e[0]
      r[col_idx[e0]]=flt(e[1]) or 0.00
     
    
    for d in ded_ret:
      d0 = '%s'%d[0]
      r[col_idx[d0]]=flt(d[1]) or 0.00
      
        
    tot_earn_ded_net_ret = sql("select gross_pay, total_deduction,net_pay from `tabSalary Slip` where name = '%s'"%r[col_idx['ID']])
    if d2 == 'Total Earning':
      r[col_idx[d2]] = flt(tot_earn_ded_net_ret[0][0]) or 0
      total_earning += flt(tot_earn_ded_net_ret[0][0]) or 0
    elif d2 == 'Total Deduction':
      r[col_idx[d2]] = flt(tot_earn_ded_net_ret[0][1]) or 0
      total_deduction += flt(tot_earn_ded_net_ret[0][1]) or 0
    elif d2 == 'Net Pay':
      r[col_idx[d2]] = flt(tot_earn_ded_net_ret[0][2]) or 0
      sum_net += flt(tot_earn_ded_net_ret[0][2]) or 0
 
 
total.append(total_lwp)
total.append(total_arr)

for lst in earn_type_lst:
  
  total_ear = 0
  for r in res:
   
    lst0 = '%s'%lst[0]
    total_ear += flt(r[col_idx[lst0]])
    
  total.append(total_ear) 
  
total.append(total_earning)
for lst in ded_type_lst:
  total_ded = 0
  for r in res:
    lst0 = '%s'%lst[0]
    total_ded += flt(r[col_idx[lst0]])
    
  total.append(total_ded) 


total.append(total_deduction)
total.append(sum_net)

res.append(total)
