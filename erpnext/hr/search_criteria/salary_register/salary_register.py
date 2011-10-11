sal_slips_ids = ''
for r in res:
  if not sal_slips_ids == '': sal_slips_ids +=","
  sal_slips_ids+="'%s'"%r[col_idx['ID']]

earn_heads =[i[0] for i in sql("select distinct e_type from `tabSS Earning Detail` where parent in (%s)"%sal_slips_ids)]
ded_heads =[i[0] for i in sql("select distinct d_type from `tabSS Deduction Detail` where parent in (%s)"%sal_slips_ids)]

col=[]

for e in earn_heads:
  l = (len(e)*9) 
  if l < 150 :
    col_width = '150px'
  else:
    col_width = '%spx'%(l)
  col.append([e,'Currency',col_width,''])

col.append(['Arrear Amount','Currency','150px',''])
col.append(['Encashment Amount','Currency','170px',''])
col.append(['Gross Pay','Currency','150px',''])

for d in ded_heads:
  l = (len(d)*9) 
  if l < 150 : col_width = '150px'
  else:  col_width = '%spx'%(l)
  col.append([d,'Currency',col_width,''])

col.append(['Total Deduction','Currency','150px',''])
col.append(['Net Pay','Currency','150px',''])

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)

grand_tot = 0
for r in res:

  for i in range(6,len(colnames)):
    if colnames[i] not in ('Arrear Amount','Encashment Amount','Net Pay','Gross Pay','Total Deduction'):
      amt = sql("select e_modified_amount from `tabSS Earning Detail` where e_type = '%s' and parent = '%s'"%(colnames[i],r[0]))
      if not amt:
        amt = sql("select d_modified_amount from `tabSS Deduction Detail` where d_type = '%s' and parent = '%s'"%(colnames[i],r[0]))
      amt = amt and amt[0][0] or 0
      r.append(flt(amt))
      
    else:
      fld_nm = cstr(colnames[i]).lower().replace(' ','_')
      errprint(fld_nm)
      tot = sql("select %s from `tabSalary Slip` where name ='%s'"%(fld_nm,r[0]))
      tot = tot and flt(tot[0][0]) or 0
      if colnames[i] == 'Net Pay':
        grand_tot += tot
      r.append(tot)
    
gt_row = ['' for i in range(len(colnames))]
gt_row[col_idx['Employee Name']] = '<b>Grand Totals</b>'
gt_row[col_idx['Net Pay']-1] = fmt_money(grand_tot)
res.append(gt_row)
