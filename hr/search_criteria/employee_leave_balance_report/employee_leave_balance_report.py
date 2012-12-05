# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

leave_types = sql("""
	SELECT name FROM `tabLeave Type`
	WHERE
		docstatus!=2 AND
		name NOT IN ('Compensatory Off', 'Leave Without Pay')""")
col=[]
col.append(['Employee ID', 'Data', '150px', ''])
col.append(['Employee Name', 'Data', '150px', ''])
col.append(['Fiscal Year', 'Data', '150px', ''])
  
for e in leave_types:
	l = (len(e[0])*9) 
	if l < 150 : col_width = '150px'
	else:  col_width = '%spx'%(l)	
	col.append([e[0],'Currency',col_width,''])

col.append(['Total Balance','Currency','150px',''])

for c in col:
	colnames.append(c[0])
	coltypes.append(c[1])
	colwidths.append(c[2])
	coloptions.append(c[3])
	col_idx[c[0]] = len(colnames)

data = res
res = []

try:
	for d in data:
		exists = 0
		ind = None
		
		# Check if the employee record exists in list 'res'
		for r in res:
			if r[0] == d[0] and r[1] == d[1]:
				exists = 1
				ind = res.index(r)
				break
		if d[3] in colnames:
			# If exists, then append the leave type data
			if exists:
				res[ind][colnames.index(d[3])] = flt(d[4]) - flt(d[5])
				res[ind][len(colnames)-1] = sum(res[ind][3:-1])
			# Else create a new row in res
			else:
				new_row = [0.0 for c in colnames]
				new_row[0] = d[0]
				new_row[1] = d[1]
				new_row[2] = d[2]
				new_row[colnames.index(d[3])] = flt(d[4]) - flt(d[5])
				new_row[len(colnames)-1] = sum(new_row[3:-1])
				res.append(new_row)
except Exception, e:
	msgprint(e)