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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from webnotes.utils import flt

if not (filter_values.get('posting_date') or filter_values.get('posting_date1')):
	msgprint("Please select From and To Posting Date", raise_exception=1)

columns = [
	['Delivery Note', 'Link', '120px', 'Delivery Note'],
	['Posting Date', 'Date', '120px', ''],
	['Posting Time', 'Data', '120px', ''],
	['Item Code', 'Link', '120px', 'Item'],
	['Item Name', 'Data', '120px', ''],
	['Description', 'Data', '120px', ''],
	['Warehouse', 'Link', '120px', 'Warehouse'],
	['Project Name', 'Link', '120px', 'Project'],
	['Quantity', 'Currency', '120px', ''],
	['Rate', 'Currency', '120px', ''],
	['Amount', 'Currency', '120px', ''],
	#['DN Item Row Id', 'Data', '120px', ''],
	['Purchase Cost', 'Currency', '150px', ''],
	['Gross Profit', 'Currency', '150px', ''],
 	['Gross Profit (%)', 'Currrency', '150px', '']
]

for c in columns:
	colnames.append(c[0])
	coltypes.append(c[1])
	colwidths.append(c[2])
	coloptions.append(c[3])
	col_idx[c[0]] = len(colnames)-1

sle = sql("""
	select 
		actual_qty, incoming_rate, voucher_no, item_code, warehouse, voucher_detail_no
	from 
		`tabStock Ledger Entry`
	where 
		voucher_type = 'Delivery Note'
		and ifnull(is_cancelled, 'No') = 'No'
	order by posting_date desc, posting_time desc, name desc
""", as_dict=1)

def get_purchase_cost(dn, item, wh, qty, dn_item_row_id):
	from webnotes.utils import flt
	global sle
 	purchase_cost = 0
	packing_items = sql("select item_code, qty from `tabSales BOM Item` where parent = %s", item)
	if packing_items:
		packing_items = [[t[0], flt(t[1])*qty] for t in packing_items]
	else:
		packing_items = [[item, qty]]
	for d in sle:
		if packing_items:
			 if d['voucher_no'] == dn \
					and [d['item_code'], flt(abs(d['actual_qty']))] in packing_items \
			 		and (not d['voucher_detail_no'] or d['voucher_detail_no'] == dn_item_row_id):
				purchase_cost += flt(d['incoming_rate'])*flt(abs(d['actual_qty']))
				packing_items.remove([d['item_code'], flt(abs(d['actual_qty']))])
		else:
			break
				
	return purchase_cost
			
out, tot_amount, tot_pur_cost = [], 0, 0
for r in res:
	purchase_cost = get_purchase_cost(r[col_idx['Delivery Note']], r[col_idx['Item Code']], \
		r[col_idx['Warehouse']], r[col_idx['Quantity']], r[-1])
	r.pop(-1)
	r.append(purchase_cost)
	
	gp = flt(r[col_idx['Amount']]) - flt(purchase_cost)
	gp_percent = r[col_idx['Amount']] and purchase_cost and \
	 	round((gp*100/flt(r[col_idx['Amount']])), 2) or 0
	r.append(fmt_money(gp))
	r.append(fmt_money(gp_percent))
	out.append(r)
	
	tot_amount += flt(r[col_idx['Amount']])
	tot_pur_cost += flt(purchase_cost)
# Add Total Row
l_row = ['' for i in range(len(colnames))]
l_row[col_idx['Project Name']] = '<b>TOTALS</b>'
l_row[col_idx['Amount']] = fmt_money(tot_amount)
l_row[col_idx['Purchase Cost']] = fmt_money(tot_pur_cost)
l_row[col_idx['Gross Profit']] = fmt_money(flt(tot_amount) - flt(tot_pur_cost))
l_row[col_idx['Gross Profit (%)']] = tot_amount and \
	round((flt(tot_amount) - flt(tot_pur_cost))*100 / flt(tot_amount), 2)
out.append(l_row)