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
based_on = filter_values.get('based_on')
# make default columns
#for r in res:
col = []
if based_on == 'Purchase Order':
  col = [['Purchase Order ID','Link','Purchase Order'],['Status','Data',''],['Project Name','Link','Project'],['Supplier','Link','Supplier'],['Supplier Name','Data',''],['% Received','Data',''],['% Billed','Data',''],['Grand Total','Currency','']] 

elif based_on == 'Purchase Invoice':
  col = [['Purchase Receipt ID','Link','Purchase Invoice'],['Status','Data',''],['Project Name','Link','Project'],['Supplier','Link','Supplier'],['Supplier Name','Data',''],['Grand Total','Currency','']]

elif based_on == 'Purchase Receipt':
  col = [['Purchase Invoice ID','Link','Purchase Receipt'],['Credit To','Data',''],['Project Name','Link','Project'],['Supplier','Link','Supplier'],['Supplier Name','Data',''],['Grand Total','Currency','']]
 
  
for c in col:
  colnames.append(c[0])
  coltypes.append(c[1])
  coloptions.append(c[2])
  l = (len(c[0])*9) 
  if l < 150 : col_width = '150px'
  else:  col_width = '%spx'%(l)
  colwidths.append(col_width)
  col_idx[c[0]] = len(colnames)-1  