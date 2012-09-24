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

# Add Columns
# ------------
from __future__ import unicode_literals
colnames[colnames.index('Rate*')] = 'Rate' 
col_idx['Rate'] = col_idx['Rate*']
col_idx.pop('Rate*')
colnames[colnames.index('Amount*')] = 'Amount' 
col_idx['Amount'] = col_idx['Amount*']
col_idx.pop('Amount*')

columns = [['Valuation Rate','Currency','150px',''],
           ['Valuation Amount','Currency','150px',''],
           ['Gross Profit (%)','Currrency','150px',''],
           ['Gross Profit','Currency','150px','']]

for c in columns:
  colnames.append(c[0])
  coltypes.append(c[1])
  colwidths.append(c[2])
  coloptions.append(c[3])
  col_idx[c[0]] = len(colnames)-1

out, tot_amount, tot_val_amount, tot_gross_profit = [], 0, 0, 0

for r in res:
  tot_val_rate = 0
  packing_list_items = sql("select item_code, warehouse, qty from `tabDelivery Note Packing Item` where parent = %s and parent_item = %s", (r[col_idx['ID']], r[col_idx['Item Code']]))
  for d in packing_list_items:
    if d[1]:
      val_rate = sql("select valuation_rate from `tabStock Ledger Entry` where item_code = %s and warehouse = %s and voucher_type = 'Delivery Note' and voucher_no = %s and is_cancelled = 'No'", (d[0], d[1], r[col_idx['ID']]))
      val_rate = val_rate and val_rate[0][0] or 0
      if r[col_idx['Quantity']]: tot_val_rate += (flt(val_rate) * flt(d[2]) / flt(r[col_idx['Quantity']]))
      else: tot_val_rate = 0

  r.append(fmt_money(tot_val_rate))

  val_amount = flt(tot_val_rate) * flt(r[col_idx['Quantity']])
  r.append(fmt_money(val_amount))

  gp = flt(r[col_idx['Amount']]) - flt(val_amount)
  
  if val_amount: gp_percent = gp * 100 / val_amount
  else: gp_percent = gp
  
  r.append(fmt_money(gp_percent))
  r.append(fmt_money(gp))
  out.append(r)

  tot_gross_profit += flt(gp)
  tot_amount += flt(r[col_idx['Amount']])
  tot_val_amount += flt(val_amount)  

# Add Total Row
# --------------
l_row = ['' for i in range(len(colnames))]
l_row[col_idx['Quantity']] = '<b>TOTALS</b>'
l_row[col_idx['Amount']] = fmt_money(tot_amount)
l_row[col_idx['Valuation Amount']] = fmt_money(tot_val_amount)
if tot_val_amount: l_row[col_idx['Gross Profit (%)']] = fmt_money((tot_amount - tot_val_amount) * 100 / tot_val_amount)
else: l_row[col_idx['Gross Profit (%)']] = fmt_money(tot_amount)
l_row[col_idx['Gross Profit']] = fmt_money(tot_gross_profit)
out.append(l_row)