# Add Columns
# ------------
based_on = filter_values.get('based_on')

columns = [[based_on,'Data','150px',''],
           ['Total Qty','Currency','150px',''],
           ['Revenue','Currency','150px',''],
           ['Valuation Amount','Currency','150px',''],
           ['Gross Profit (%)','Currrency','150px',''],
           ['Gross Profit','Currency','150px','']]           

for c in columns:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1



def make_child_lst(based_on,name):
  rg = sql("select lft, rgt from `tab%s` where name = '%s'"%(based_on,name))
  ch_name = sql("select name from `tab%s` where lft between %d and %d"%(based_on,int(rg[0][0]),int(rg[0][1])))
  chl ='('
  flag = 1
  for c in ch_name:
    if flag == 1:
     chl += "'%s'"%c[0]
     flag = 2
    else:
      chl +=",'%s'"%c[0]

  chl +=")"
  return chl



for r in res:

  qty, rate, amt, tot_val_rate, val_amount = 0, 0, 0, 0,0
  cn = make_child_lst(based_on,r[0].strip())



  if based_on == 'Item Group':
  
    dn = sql("select name from `tabItem` where item_group in %s"%(cn))
    for n in dn:
      
      dt = sql("select sum(qty),sum(amount) from `tabDelivery Note Detail` where item_code ='%s' and docstatus = 1"%n[0])  
          
      qty += dt[0][0] and dt[0][0] or 0
      amt += dt[0][1] and dt[0][1] or 0  
      prt = sql("select distinct t1.name from `tabDelivery Note` t1, `tabDelivery Note Detail` t2 where t1.name = t2.parent and t2.item_code = '%s' and t1.docstatus = 1 and t2.docstatus =1 order by t1.name"%n[0])
      for p in prt:
        d1 = sql("select qty from `tabDelivery Note Detail` where parent = '%s' and parenttype ='Delivery Note' and docstatus =1 and item_code = '%s'"%(p[0],n[0]))
        for t in d1:
          tot_val_rate = 0
          packing_list_items = sql("select item_code, warehouse, qty from `tabDelivery Note Packing Detail` where parent = '%s' and parent_item = '%s' and docstatus = 1 order by item_code, warehouse, qty"%(p[0],n[0]))
                           
          for d in packing_list_items:
            if d[1]:
              val_rate = sql("select valuation_rate from `tabStock Ledger Entry` where item_code = '%s' and warehouse = '%s' and voucher_type = 'Delivery Note' and voucher_no = '%s' and is_cancelled = 'No'"%(d[0], d[1], p[0]))
              
              val_rate = val_rate and val_rate[0][0] or 0
              
              tot_val_rate += t[0] and (flt(val_rate) * flt(d[2]) / flt(t[0])) or 0
          val_amount += flt(tot_val_rate) * flt(t[0])  
  elif based_on == 'Territory':
    

    dn = sql("select name from `tabDelivery Note` where territory in %s and docstatus =1 order by name"%(cn))

    for n in dn:

      dt = sql("select sum(qty), sum(amount) from `tabDelivery Note Detail` where parent = '%s' and docstatus = 1"%n[0])
      qty += dt[0][0] and dt[0][0] or 0
      amt += dt[0][1] and dt[0][1] or 0

      d1 = sql("select item_code,qty from `tabDelivery Note Detail` where parent = '%s' and parenttype ='Delivery Note' and docstatus =1"%n[0])

      for t in d1:
        tot_val_rate = 0
        packing_list_items = sql("select item_code, warehouse, qty from `tabDelivery Note Packing Detail` where parent = '%s' and parent_item = '%s' and docstatus = 1 order by item_code, warehouse,qty"%(n[0],t[0]))
       
        for d in packing_list_items:
          if d[1]:
            
            val_rate = sql("select valuation_rate from `tabStock Ledger Entry` where item_code = '%s' and warehouse = '%s' and voucher_type = 'Delivery Note' and voucher_no = '%s' and is_cancelled = 'No'"%(d[0], d[1], n[0]))
            val_rate = val_rate and val_rate[0][0] or 0
            
            tot_val_rate += t[1] and (flt(val_rate) * flt(d[2]) / flt(t[1])) or 0
        val_amount += flt(tot_val_rate) * flt(t[1])
  r.append(fmt_money(qty))

  r.append(fmt_money(amt))
  gp = flt(r[col_idx['Revenue']]) - flt(val_amount)
  
  if val_amount: gp_percent = gp * 100 / flt(val_amount)
  else: gp_percent = gp
  gp_percent = '%0.2f'%gp_percent

      

  r.append(fmt_money(val_amount))
  r.append(fmt_money(gp_percent))
  r.append(fmt_money(gp))