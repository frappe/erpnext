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
if not filter_values.get('tds_category'):
  msgprint("Please enter TDS Category")
  raise Exception

l = [
      ['ID','150px','Link','TDS Payment'],
      ['Challan ID No.','100px','Data',''], 
      ['Party Name','200px','Link','Account'], 
      ['Amount paid / credited','100px','Currency',''], 
      ['Date of payment / credit','100px','Date',''], 
      ['TDS','100px','Currency',''], 
      ['Cess on TDS','100px','Currency',''], 
      ['Total Tax Amount','100px','Currency',''], 
      ['PAN of the deductee','100px','Data',''],
      ['Total Tax Deposited','100px','Currency',''],
      ['Date of Deduction','100px','Date',''], 
      ['Rate at which deducted','100px','Currency',''], 
      ['Reason for Non-deduction / Lower deduction','100px','Data',''], 
      ['Grossing up indicator','100px','Data',''], 
      ['Deductee Code','100px','Data',''], 
      ['Mode','100px','Data','']
    ]

for i in l:
  colnames.append(i[0])
  colwidths.append(i[1])
  coltypes.append(i[2])
  coloptions.append(i[3])
  col_idx[i[0]] = len(colnames)-1

for r in res:
  r.append(r[col_idx['Total Tax Amount']])
  for i in range(0,6):
    r.append('')