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
col = [['In Store Period (in days)', 'Data', '']]
for c in col:
  colnames.append(str(c[0]))
  coltypes.append(str(c[1]))
  colwidths.append('150px')
  coloptions.append(str(c[2]))
  col_idx[str(c)] = len(colnames) - 1

import datetime
for r in res:
  if r[col_idx['Purchase Date']]:
    dt = (datetime.date.today() - getdate(r[col_idx['Purchase Date']])).days
  else:
    dt = ''
  r.append(dt)