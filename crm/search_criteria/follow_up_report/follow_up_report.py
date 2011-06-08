follow_up_on = filter_values.get('follow_up_on')

cols = [['Document Type', 'Data', '150px', '']
        ,['Document', 'Link', '150px', follow_up_on]
        ,['Follow Up Date', 'Date', '150px', '']
        ,['Description','Data','300px','']
        ,['Follow Up Type','Data','150px','']
        ,['Follow Up By','Link','150px','Sales Person']
       ]

for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1
