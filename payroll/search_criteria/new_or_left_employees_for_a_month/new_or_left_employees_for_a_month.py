status = filter_values.get('status')
month = filter_values.get('month')


if status == 'Active' and not status == 'Left':
  col = [['Employee', 'Link', 'Employee'], ['Employee Name', 'Data', ''], ['Employee Number', 'Data', ''], ['Employment Type','Link','Employment Type'],['Scheduled Confirmation Date','Data',''],['Final Confirmation Date','Data',''],['Contract End Date','Data',''],['Branch','Link','Branch'],['Department','Link','Department'],['Designation','Link','Designation'],['Reports to','Link','Employee'],['Grade','Link','Grade']]

elif status == 'Left' and not status == 'Active':
  col = [['Employee', 'Link', 'Employee'], ['Employee Name', 'Data', ''], ['Employee Number', 'Data', ''], ['Resignation Letter Date','Data',''],['Relieving Date','Data',''],['Notice - Number of Days','Data',''],['Reason for Leaving','Data',''],['Leave Encashed?','Data',''],['Encashment Date','Data',''],['Reason for Resignation','Data','']]

else:
  col = [['Employee', 'Link', 'Employee'], ['Employee Name', 'Data', ''], ['Employee Number', 'Data', ''], ['Employment Type','Link','Employment Type'],['Scheduled Confirmation Date','Data',''],['Final Confirmation Date','Data',''],['Contract End Date','Data',''],['Branch','Link','Branch'],['Department','Link','Department'],['Designation','Link','Designation'],['Reports to','Link','Employee'],['Grade','Link','Grade'],['Resignation Letter Date','Data',''],['Relieving Date','Data',''],['Notice - Number of Days','Data',''],['Reason for Leaving','Data',''],['Leave Encashed?','Data',''],['Encashment Date','Data',''],['Reason for Resignation','Data','']]

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append('150px')
  coloptions.append(c[2])
  
  col_idx[c[0]] = len(colnames)-1


for c in range(0,len(colnames)):
  l = (len(colnames[c])*9) 
  if l < 150 : col_width = '150px'
  else:  col_width = '%spx'%(l)

  colwidths[c] = col_width

for r in res:

  if status == 'Active':
    ret = sql("select employment_type,scheduled_confirmation_date,final_confirmation_date,contract_end_date,branch,department,designation,reports_to,grade from `tabEmployee` where name = %s",r[0])

  elif status == 'Left':
    ret = sql("select resignation_letter_date,relieving_date,notice_number_of_days,reason_for_leaving,leave_encashed,encashment_date,reason_for_resignation from `tabEmployee` where name =%s",r[0])

  else:
    ret = sql("select employment_type,scheduled_confirmation_date,final_confirmation_date,contract_end_date,branch,department,designation,reports_to,grade,resignation_letter_date,relieving_date,notice_number_of_days,reason_for_leaving,leave_encashed,encashment_date,reason_for_resignation from `tabEmployee` where name = %s",r[0])

  ret = ret and ret[0] or []
  for t in ret:
    r.append(cstr(t))
