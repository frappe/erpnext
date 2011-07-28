data =[
		['Lessee Name','Data','300px',''],
		['Below 30 Days','Currency','120px',''],
		['Below 90 Days','Currency','120px',''],
		['Below 180 Days','Currency','120px',''],
		['Below 360 Days','Currency','120px',''],
		['Above 360 Days','Currency','120px',''],
	]

for d in data:
	colnames.append(d[0])
	coltypes.append(d[1])
	colwidths.append(d[2])
	coloptions.append(d[3])
	col_idx[d[0]] = len(colnames)-1

