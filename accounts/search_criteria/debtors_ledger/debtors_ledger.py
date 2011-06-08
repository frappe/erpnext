#get company
company = filter_values.get('company') or get_defaults()['company']

#get company letter head
l_head = sql("select letter_head from `tabCompany` where name='%s'" % company)
l_head = l_head and l_head[0][0] or ''

# Posting date, fiscal year and year start date
#-----------------------------------------------
if not filter_values.get('posting_date') or not filter_values.get('posting_date1'):
  msgprint("Please enter From Date and To Date")
  raise Exception
else:
  from_date = filter_values['posting_date']
  to_date = filter_values['posting_date1']

ysd, from_date_year = sql("select year_start_date, name from `tabFiscal Year` where %s between year_start_date and date_add(year_start_date,interval 1 year)",from_date)[0]


# define columns
#---------------
col = []
col.append(['Date','Date','80px',''])
col.append(['Detail','Text','475px',''])
col.append(['Debit','Currency','75px',''])
col.append(['Credit','Currency','75px',''])

for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)


total_debit, total_credit, total_opening, total_diff = 0,0,0,0

#total query
q = query.split('WHERE')[1].split('LIMIT')
if len(q) > 2:
  query_where_clause = 'LIMIT'.join(q[:-1])
else:
  query_where_clause = q[0]

tot = sql('select sum(`tabGL Entry`.debit),sum(`tabGL Entry`.credit) from `tabGL Entry`, tabAccount where %s' % query_where_clause)

for t in tot:
  total_debit += t and flt(t[0]) or 0
  total_credit += t and flt(t[1]) or 0

total_diff = total_debit - total_credit

# opening
account = filter_values.get('account')
if account:
  acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt, group_or_ledger from tabAccount where name = '%s'" % account)
  opening_bal = get_obj('GL Control').get_as_on_balance(account, from_date_year, add_days(from_date, -1), acc_det[0][0], acc_det[0][2], acc_det[0][3])[2]
  if acc_det[0][0] == 'Credit':
    opening_bal =  -1*opening_bal
  

out = []
count = 0
for r in res:
  count +=1
  det = r[1].split('~~~')
  if from_export == 1:
    a = "Account: " + det[0] + NEWLINE + det[1] + NEWLINE + "Against: " + det[2] + NEWLINE + "Voucher No: " + det[4]
  else:
    a = "Account: <b>" + det[0]+ "</b>" + NEWLINE + "<div class='comment'>" +det[1]+ "</div><div class = 'comment' style='padding-left:12px'>Against: <b>" + det[2] + "</b></div><div class = 'comment' style='padding-left:12px'>Voucher No: <span class='link_type' onclick='loaddoc(" + '"' + det[3] +'", ' + '"' + det[4] +'"' + ")'>" + det[4] + "</span></div>"
  r[1] = a
  out.append(r)

if total_debit != 0 or total_credit != 0:
  # Total debit/credit
  t_row = ['' for i in range(len(colnames))]
  t_row[1] = 'Total'
  t_row[col_idx['Debit']-1] = total_debit 
  t_row[col_idx['Credit']-1] = total_credit 
  out.append(t_row)
  
  # opening
  if account:
    t_row = ['' for i in range(len(colnames))]
    t_row[1] = 'Opening Balance on '+ from_date
    t_row[col_idx['Debit']-1] = opening_bal
    out.append(t_row)
  
  # diffrence (dr-cr)
  t_row = ['' for i in range(len(colnames))]
  t_row[1] = 'Total(Dr-Cr)'
  t_row[col_idx['Debit']-1] = total_diff 
  out.append(t_row)

  # closing
  if account:
    t_row = ['' for i in range(len(colnames))]
    t_row[1] = 'Closing Balance on ' + to_date
    t_row[col_idx['Debit']-1] = flt(opening_bal) + flt(total_diff )
    out.append(t_row)
  
# Print Format
myheader = """<table width = '100%%'><tr><td>"""+l_head+"""</td>
</tr>
<tr> <td>
<div><h3> %(acc)s </h3></div>
<div>Ledger Between %(fdt)s and %(tdt)s </div></td></tr></table><br>

  """ % {'acc':account,
         'fdt':from_date,
         'tdt':to_date}
 
page_template = myheader+"<div>%(table)s</div>"