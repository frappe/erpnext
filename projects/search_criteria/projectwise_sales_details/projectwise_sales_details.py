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

cols=[]

if based_on == 'Sales Order':  
  cols = [['Sales Order No','Link','150px','Sales Order'], ['Order Type','Data','100px',''], ['Status','Data','100px',''], ['Project Name','Link','150px','Project'], ['Customer','Link','150px','Customer'], ['Customer Name','Data','200px',''], ['% Delivered','Currency','100px',''], ['% Billed','Currency','100px',''], ['Grand Total','Currency','150px','']]

elif based_on == 'Delivery Note':
  cols = [['Delivery Note No','Link','150px','Delivery Note'], ['Status','Data','100px',''], ['Project Name','Link','200px','Project'], ['Customer','Link','150px','Customer'], ['Customer Name','Data','200px',''], ['% Installed','Currency','100px',''], ['% Billed','Currency','100px',''], ['Grand Total','Currency','150px','']]

elif based_on == 'Sales Invoice':
  cols = [['Sales Invoice No','Link','150px','Sales Invoice'], ['Debit To','Data','150px',''], ['Project Name','Link','200px','Project'], ['Customer','Link','150px','Customer'], ['Customer Name','Data','200px',''], ['Grand Total','Currency','150px','']]


for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1