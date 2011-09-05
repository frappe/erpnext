
opt = filter_values.get('based_on')
opt_dict = {'Territory':'territory', 'Item Group':'item_group'}

# ADD NEW COLUMNS
row_list = [[opt,'Data','150px',''],
           ['Out of AMC','Int','150px',''],
           ['Under AMC','Int','150px',''],
           ['Out of Warranty','Int','150px',''],
           ['Under Warranty','Int','150px',''],
           ['Total','Int','150px','']]

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
  lft_rgt = sql("select lft, rgt from `tab%s` where name = '%s'" % (opt,r[col_idx[opt]].strip()))
  
  
  det = sql("select COUNT(CASE WHEN t1.amc_expiry_date < '%s' THEN t1.name ELSE NULL END), COUNT(CASE WHEN t1.amc_expiry_date >= '%s' THEN t1.name ELSE NULL END), COUNT(CASE WHEN t1.warranty_expiry_date < '%s' THEN t1.name ELSE NULL END), COUNT(CASE WHEN t1.warranty_expiry_date >= '%s' THEN t1.name ELSE NULL END) from `tabSerial No` t1, `tab%s` t2 where t1.%s = t2.name and t2.lft>= '%s' and t2. rgt <= '%s' and t1.status not in ('In Store', 'Scrapped','Not in Use') and ifnull(item_group,'')!='' and ifnull(territory,'')!=''" %(nowdate,nowdate,nowdate,nowdate,opt, opt_dict[opt], lft_rgt[0][0], lft_rgt[0][1]))
  
  r.append(cint(det[0][0]))
  r.append(cint(det[0][1]))
  r.append(cint(det[0][2]))
  r.append(cint(det[0][3]))
  tot = cint(det[0][0]) + cint(det[0][1]) + cint(det[0][2]) + cint(det[0][3])
  r.append(tot)
  out.append(r)
