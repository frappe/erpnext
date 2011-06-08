# ADD NEW COLUMNS
row_list = [['Item Group','Data','150px',''],
            ['Out of AMC','Int','150px',''],
            ['Under AMC','Int','150px',''],
            ['Out of Warranty','Int','150px',''],
            ['Under Warranty','Int','150px',''],
            ['Total','Int','150px','']
           ]

for r in row_list:
  colnames.append(r[0])
  coltypes.append(r[1])
  colwidths.append(r[2])
  coloptions.append(r[3])
  col_idx[r[0]] = len(colnames)-1


#ADD VALUES TO THE COLUMN
out=[]
oa,ua,ow,uw,sum=0,0,0,0,0
nowdate = nowdate()
for r in res:
  cc = r[col_idx['Territory']]
  item_groups = sql("select distinct item_group from `tabSerial No` where territory = '%s' and item_group like '%%%s'" %(cc,filter_values.get('item_group')))
  
  for col in range(len(colnames)-1): # this would make all first row blank. just for look
    r.append('')
  out.append(r)
  
  # Add Totals for each Territory
  # -----------------------------
  det = sql("select COUNT(CASE WHEN amc_expiry_date > '%s' THEN name ELSE NULL END), COUNT(CASE WHEN amc_expiry_date <= '%s' THEN name ELSE NULL END), COUNT(CASE WHEN warranty_expiry_date > '%s' THEN name ELSE NULL END), COUNT(CASE WHEN warranty_expiry_date <= '%s' THEN name ELSE NULL END) from `tabSerial No` where territory = '%s' and item_group like '%%%s'" %(nowdate,nowdate,nowdate,nowdate,cc,filter_values.get('item_group')))
  r[col_idx['Item Group']] = ''

  r[col_idx['Out of AMC']] = cstr(det[0][0])
  r[col_idx['Under AMC']] = cstr(det[0][1])
  r[col_idx['Out of Warranty']] = cstr(det[0][2])
  r[col_idx['Under Warranty']] = cstr(det[0][3])
  tot = cint(det[0][0]) + cint(det[0][1]) + cint(det[0][2]) + cint(det[0][3])
  r[col_idx['Total']] = cstr(tot)


  oa  += cint(det[0][0])
  ua  += cint(det[0][1])
  ow  += cint(det[0][2])
  uw  += cint(det[0][3])
  sum += tot

  
  # Add Brand Details belonging to Territory
  # ----------------------------------------
  for br in item_groups:
    br_det = sql("select COUNT(CASE WHEN amc_expiry_date > '%s' THEN name ELSE NULL END), COUNT(CASE WHEN amc_expiry_date <= '%s' THEN name ELSE NULL END), COUNT(CASE WHEN warranty_expiry_date > '%s' THEN name ELSE NULL END), COUNT(CASE WHEN warranty_expiry_date <= '%s' THEN name ELSE NULL END) from `tabSerial No` where territory = '%s' and item_group = '%s'"%(nowdate,nowdate,nowdate,nowdate,cc,br[0]))
    t_row = ['' for i in range(len(colnames))]
    t_row[col_idx['Item Group']] = br[0]
   
    t_row[col_idx['Out of AMC']] = cint(br_det[0][0])
    t_row[col_idx['Under AMC']] = cint(br_det[0][1])
    t_row[col_idx['Out of Warranty']] = cint(br_det[0][2])
    t_row[col_idx['Under Warranty']] = cint(br_det[0][3])
    tot = cint(br_det[0][0]) + cint(br_det[0][1]) + cint(br_det[0][2])+ cint(br_det[0][3])
    t_row[col_idx['Total']] = tot
    out.append(t_row)
  

#ADD NEW ROW
# ----------
newrow=['','TOTAL',oa,ua,ow,uw,sum]
out.append(newrow)
res=out