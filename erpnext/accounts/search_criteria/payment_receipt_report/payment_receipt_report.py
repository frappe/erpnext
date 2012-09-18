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
if not filter_values.get('posting_date'):
  msgprint("Enter From Posting Date.")
  raise Exception

if not filter_values.get('posting_date1'):
  msgprint("Enter To Posting Date.")
  raise Exception

if not filter_values.get('company'):
  msgprint("Select Company to proceed.")
  raise Exception



col_list = [['Account', 'Link', '150px', 'Account']
           ,['Total', 'Currency', '150px', '']
           ]
           
for c in col_list:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames) - 1
