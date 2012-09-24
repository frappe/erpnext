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
out=[]
qty,amt,del_qty,bill_amt=0,0,0,0

for r in res:
  qty += flt(r[col_idx['Quantity']])
  amt += flt(r[col_idx['Amount*']])
  del_qty += flt(r[col_idx['Delivered Qty']])
  bill_amt += flt(r[col_idx['Billed Amt']])
  out.append(r)


#Add the totals row
l_row = ['' for i in range(len(colnames))]
l_row[col_idx['Item Name']] = '<b>TOTALS</b>'
l_row[col_idx['Quantity']] = qty
l_row[col_idx['Amount*']] = amt
l_row[col_idx['Delivered Qty']] = del_qty
l_row[col_idx['Billed Amt']] = bill_amt
out.append(l_row)
