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
if filter_values.get('based_on') == 'Sales Invoice':
  based_on_dt = 'Sales Invoice'
else:
  based_on_dt = filter_values.get('based_on')

cols = [
	[filter_values.get('based_on'), 'Link','150px', based_on_dt],
	['Transaction Date', 'Date', '120px', ''], 
	['Customer', 'Link','150px','Customer'], 
	['Net Total', 'Currency', '80px', ''], 
	['Tax Account', 'Link','150px','Account'], 
	['Description', 'Text','120px',''], 
	['Tax Rate', 'Currency', '80px', ''], 
	['Tax Amount', 'Currency', '80px', '']
]

for c in cols:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1
