# use This in Query 
# AND `tabAccount`.debit_or_credit = "Debit" AND `tabAccount`.`is_pl_account` = "Yes"



# validate Filters
if not filter_values.get('fiscal_year'):
  msgprint("Please Select Fiscal Year")
  raise Exception
if not filter_values.get('period'):
  msgprint("Please Select Period")
  raise Exception
  
# Get Values from fliters 
fiscal_year = filter_values.get('fiscal_year')
period = filter_values.get('period')

mon_list = []
data = {'start_date':0, 'end_date':1}
def make_month_list(append_colnames, start_date, mon_list, period, colnames, coltypes, colwidths, coloptions, col_idx):
  count = 1
  if period == 'Quarterly' or period == 'Half Yearly' or period == 'Annual': mon_list.append([str(start_date)])
  for m in range(12):
    # get last date
    last_date = str(sql("select LAST_DAY('%s')" % start_date)[0][0])
    
    # make mon_list
    if period == 'Monthly' :
      mon_list.append([start_date, last_date])
      # add months as Column names
      month_name = sql("select MONTHNAME('%s')" % start_date)[0][0]
      append_colnames(str(month_name)[:3], colnames, coltypes, colwidths, coloptions, col_idx)
      
    # get start date
    start_date = str(sql("select DATE_ADD('%s',INTERVAL 1 DAY)" % last_date)[0][0])
    if period == 'Quarterly' and count % 3 == 0: 
     
      mon_list[len(mon_list) - 1 ].append(last_date)
      # add Column names
      append_colnames('Q '+ str(count / 3), colnames, coltypes, colwidths, coloptions, col_idx)
      if count != 12: mon_list.append([start_date])
    
    if period == 'Half Yearly' and count % 6 == 0 :
      mon_list[len(mon_list) - 1 ].append(last_date)
      # add Column Names
      append_colnames('H'+str(count / 6), colnames, coltypes, colwidths, coloptions, col_idx)
      if count != 12: mon_list.append([start_date])
    if period == 'Annual' and count % 12 == 0:
      mon_list[len(mon_list) - 1 ].append(last_date)
      append_colnames('', colnames, coltypes, colwidths, coloptions, col_idx)
    count = count +1

def append_colnames(name, colnames, coltypes, colwidths, coloptions, col_idx):
  col = ['Budget', 'Actual', 'Variance']
  for c in col:
    colnames.append(str(c) + ' (' + str(name) +')' )
    coltypes.append('Currency')
    colwidths.append('150px')
    coloptions.append('')
    col_idx[str(c) + ' (' + str(name) +')' ] = len(colnames) - 1

col = ['Cost Center', 'Account', 'Budget Allocated', 'Distribution Id']
for c in col:
  colnames.append(str(c))
  coltypes.append((c=='Budget Allocated') and'Currency' or 'Link')
  colwidths.append('150px')
  coloptions.append((c=='Budget Allocated') and '' or (c == 'Distribution Id') and 'Budget Distribution' or c) 
  col_idx[str(c)] = len(colnames) - 1

start_date = get_value('Fiscal Year', fiscal_year, 'year_start_date')
if not start_date:
  msgprint("Please Define Year Start Date for Fiscal Year " + str(fiscal_year))
  raise Exception
start_date = start_date.strftime('%Y-%m-%d')
make_month_list(append_colnames, start_date, mon_list, period, colnames, coltypes, colwidths, coloptions, col_idx)

# Get Object Of GL Control

glc_obj = get_obj('GL Control')
bc_obj = get_obj('Budget Control')

for r in res:
  count = 0
  for idx in range(4, len(colnames), 3):
    r.append(bc_obj.get_monthly_budget( r[3], fiscal_year, mon_list[count][data['start_date']], mon_list[count][data['end_date']], r[2]))
    r.append(glc_obj.get_period_difference(r[1] + '~~~' + mon_list[count][data['start_date']] + '~~~' + mon_list[count][data['end_date']], r[0]))
    r.append(r[idx] - r[idx + 1])
    count = count +1
