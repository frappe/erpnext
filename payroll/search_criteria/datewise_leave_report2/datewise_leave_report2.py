leave_type_lst = sql("select name from `tabLeave Type` where is_active = 'Yes'")

li=['Total Opening']
if leave_type_lst:
  for lst in leave_type_lst:
  
    li.append(lst[0])

li.append('Total Closing')



for d in li:
  colnames.append(d)
  colwidths.append("100px")
  coltypes.append("Currency")
  coloptions.append("")
  col_idx[d] = len(colnames)-1
  for r in res:
    
    r.append("0")


for r in res:
  for d1 in li:
    d2 = '%s'%d1
    if d2 == 'Total Opening':
      ret_all = sql("select sum(total_leave) from `tabLeave Transaction` where leave_transaction_type = 'Allocation' and employee = '%s' and %s <= to_date and docstatus = 1 and fiscal_year = '2010-2011'" %(r[col_idx['Employee']],filter_values['from_date']))
      
      #query = "(SUM(CASE WHEN leave_transaction_type = 'Allocation'  THEN total_leave ELSE 0 END)-SUM(CASE WHEN leave_transaction_type = 'Deduction' AND leave_type != 'Leave Without Pay' THEN total_leave ELSE 0 END))"
      #query1 = "select " + query + " from `tabLeave Transaction` where employee = '%s' and %s <= to_date and docstatus = 1"
      #sum_total_leave = sql(query1%(r[col_idx['Employee']],filter_values['from_date']))
      #r[col_idx[d2]] = flt(sum_total_leave[0][0]) or 0
      
    elif d2 == 'Total Closing':
      query = "(SUM(CASE WHEN leave_transaction_type = 'Allocation' AND leave_type != 'Leave Without Pay' AND leave_type != 'Compensatory Off' THEN total_leave ELSE 0 END)-SUM(CASE WHEN leave_transaction_type = 'Deduction' AND leave_type != 'Leave Without Pay' THEN total_leave ELSE 0 END))"
      query1 = "select " + query + " from `tabLeave Transaction` where employee = '%s' and %s <= to_date and docstatus = 1"
      sum_total_leave = sql(query1%(r[col_idx['Employee']],filter_values['to_date']))
      r[col_idx[d2]] = flt(sum_total_leave[0][0]) or 0
      
    elif leave_type_lst:
      query = "SUM(CASE WHEN leave_transaction_type = 'Deduction' THEN total_leave ELSE 0 END)"
      query1 = "select " + query + " from `tabLeave Transaction` where leave_type = '%s' and employee = '%s' and (from_date <= %s <= to_date or from_date <= %s <= to_date) and docstatus = 1"
      sum_total_leave = sql(query1%(d1,r[col_idx['Employee']],filter_values['from_date'],filter_values['to_date']))
      r[col_idx[d2]] = flt(sum_total_leave[0][0]) or 0