# ********************************************* INITIALIZATION *******************************************
out = []

# Filter Values
# =============================================
based_on = filter_values.get('based_on')
group_by = filter_values.get('group_by')
trans = filter_values.get('transaction')
period = filter_values.get('period')
order_type = filter_values.get('order_type')
company = filter_values.get('company')
fiscal_year = filter_values.get('fiscal_year')
item = filter_values.get('item')
item_group = filter_values.get('item_group')
customer = filter_values.get('customer')
customer_group = filter_values.get('customer_group')
territory = filter_values.get('territory')
supplier = filter_values.get('supplier')
supplier_type = filter_values.get('supplier_type')



# ********************************************* SET DEFAULTS **************************************************
# Details Table
# --------------
if trans == 'Sales Invoice': trans = 'Receivable Voucher'
elif trans == 'Purchase Invoice': trans = 'Payable Voucher'

trans_det = trans+' Detail'

if trans == 'Receivable Voucher': trans_det = 'RV Detail'
elif trans == 'Payable Voucher': trans_det = 'PV Detail'
elif trans == 'Purchase Order': trans_det = 'PO Detail'

col_names, query_val = get_obj('TA Control').get_single_year_query_value(fiscal_year, period, trans, trans_det)
query_val += 'SUM(t2.qty), SUM(t2.amount)'

col_names.append('Total (Qty)')
col_names.append('Total (Amt)')


# ********************************************* VALIDATIONS ***************************************************
if (based_on in ['Customer','Customer Group','Territory'] and group_by == 'Supplier') or (based_on in ['Supplier','Supplier Type'] and group_by == 'Customer'):
  msgprint("Sorry! You cannot group Trend Analyzer based on %s by %s" % (based_on,group_by))
  raise Exception

if based_on == group_by:
  msgprint("Based On and Group By value cannot be same for Trend Analyzer")
  raise Exception


# ********************************************** ADD COLUMNS **********************************************
cols = [[based_on, 'Data', '300px', '']]
cr = 1
if based_on == 'Item':
  cols.append(['Item Name','Data','200px',''])
  cr = 2
elif based_on == 'Customer':
  cols.append(['Territory','Link','150px','Territory'])
  cr = 2
elif based_on == 'Supplier':
  cols.append(['Supplier Type','Link','150px','Supplier Type'])
  cr = 2
if group_by:
  cr += 1

if group_by:
  cols.append([group_by,'Data','150px',''])

for c in col_names:
  cols.append([c,'Currency','150px',''])

for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1


# ******************************************* ADDITIONAL CONDITION ************************************************
add_cond = ' t2.parent = t1.name AND t1.company = "%s" AND t1.fiscal_year = "%s" and t1.docstatus = 1' % (company, fiscal_year)
add_tab = ' `tab'+trans+'` t1, `tab'+trans_det+'` t2'
if order_type: add_cond += ' AND t1.order_type = "%s"' % order_type


# Item
if item or based_on == 'Item':
  add_cond += ' AND t2.item_code = "%s"' % (based_on != 'Item' and item or '%(value)s')

# Item Group
if item_group or based_on == 'Item Group':
  add_tab += ' ,`tabItem` t3, `tabItem Group` t4 '
  add_cond += ' AND t3.name = t2.item_code AND t3.item_group = t4.name and (t4.name = "%s" or t4.name IN (SELECT t5.name FROM `tabItem Group` t5,`tabItem Group` t6 WHERE t5.lft BETWEEN t6.lft and t6.rgt and t5.docstatus !=2 and ifnull(t5.is_group,"No") = "No" and t6.name = "%s"))' % (based_on != 'Item Group' and item_group or '%(value)s', based_on != 'Item Group' and item_group or '%(value)s')

# Customer
if customer or based_on == 'Customer':
  add_cond += ' AND t1.customer = "%s"' % (based_on != 'Customer' and customer or '%(value)s')

# Customer Group
if customer_group or based_on == 'Customer Group':
  add_tab += ' ,`tabCustomer` t7, `tabCustomer Group` t8 '
  add_cond += ' AND t7.name = t1.customer AND t7.customer_group = t8.name and (t8.name = "%s" or t8.name IN (SELECT t9.name FROM `tabCustomer Group` t9,`tabCustomer Group` t10 WHERE t9.lft BETWEEN t10.lft and t10.rgt and t9.docstatus !=2 and ifnull(t9.is_group,"No") = "No" and t10.name = "%s"))' % (based_on != 'Customer Group'  and customer_group or '%(value)s', based_on != 'Customer Group'  and customer_group or '%(value)s')
  
# Territory
if territory or based_on == 'Territory':
  add_tab += ' ,`tabTerritory` t11 '
  add_cond += ' AND t1.territory = t11.name AND t1.territory = t11.name and (t11.name = "%s" or t11.name IN (SELECT t12.name FROM `tabTerritory` t12,`tabTerritory` t13 WHERE t12.lft BETWEEN t13.lft and t13.rgt and t12.docstatus !=2 and ifnull(t12.is_group,"No") = "No" and t13.name = "%s"))' % (based_on != 'Territory' and territory or '%(value)s', based_on != 'Territory' and territory or '%(value)s')

# Supplier
if supplier or based_on == 'Supplier':
  add_cond += ' AND t1.supplier = "%s"' % (based_on != 'Supplier' and supplier or '%(value)s')
  
# Supplier Type
if supplier_type or based_on == 'Supplier Type':
  add_tab += ' ,`tabSupplier` t14, `tabSupplier Type` t15 '
  add_cond += ' AND t14.name = t1.supplier AND t14.supplier_type = t15.name and t15.name = "%s"' % (based_on != 'Supplier Type' and supplier_type or '%(value)s')

  
# Column to be seleted for group by condition
# ==============================================
sel_col = ''
if group_by == 'Item':
  sel_col = 't2.item_code'
elif group_by == 'Customer':
  sel_col = 't1.customer'
elif group_by == 'Supplier':
  sel_col = 't1.supplier'
  
  
# ********************************************** Result Set ************************************************
for r in res:
  main_det = sql("SELECT %s FROM %s WHERE %s" % (query_val, add_tab, add_cond % {'value':cstr(r[col_idx[based_on]]).strip()}))
  if group_by:
    for col in range(cr,cr+1): # this would make all first row blank. just for look
      r.append('')
  if main_det[0][len(colnames) - cr - 1]:
    for d in range(len(colnames) - cr):
      r.append(flt(main_det[0][d]))
    out.append(r)
    
    if group_by:
      flag = 1
      # check for root nodes
      if based_on in ['Item Group','Customer Group','Territory']:
        is_grp = sql("select is_group from `tab%s` where name = '%s'" % (based_on, cstr(r[col_idx[based_on]]).strip()))
        is_grp = is_grp and cstr(is_grp[0][0]) or ''
        if is_grp != 'No':
          flag = 0

      if flag == 1:	
        det = [x[0] for x in sql("SELECT DISTINCT %s FROM %s where %s" % (sel_col, add_tab, add_cond % {'value':cstr(r[col_idx[based_on]]).strip()}))]

        for des in range(len(det)):
          t_row = ['' for i in range(len(colnames))]
          t_row[col_idx[group_by]] = cstr(det[des])
          gr_det = sql("SELECT %s FROM %s WHERE %s = '%s' and %s" % (query_val, add_tab, sel_col, cstr(det[des]), add_cond % {'value':cstr(r[col_idx[based_on]]).strip()}))
          for d in range(len(col_names)):
            t_row[col_idx[col_names[d]]] = flt(gr_det[0][d])
          out.append(t_row)