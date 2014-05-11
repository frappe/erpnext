# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from stock.utils import get_buying_amount, get_sales_bom_buying_amount

def execute(filters=None):
	if not filters: filters = {}
	
	stock_ledger_entries = get_stock_ledger_entries(filters)
	source = get_source_data(filters)
	item_sales_bom = get_item_sales_bom()
	
	columns = ["Delivery Note/Sales Invoice::120", "Link::30", "Posting Date:Date", "Posting Time", 
		"Item Code:Link/Item", "Item Name", "Description", "Warehouse:Link/Warehouse",
		"Qty:Float", "Selling Rate:Currency", "Avg. Buying Rate:Currency", 
		"Selling Amount:Currency", "Buying Amount:Currency",
		"Gross Profit:Currency", "Gross Profit %:Percent", "Project:Link/Project"]
	data = []
	for row in source:
		selling_amount = flt(row.amount)
		
		item_sales_bom_map = item_sales_bom.get(row.parenttype, {}).get(row.name, webnotes._dict())
		
		if item_sales_bom_map.get(row.item_code):
			buying_amount = get_sales_bom_buying_amount(row.item_code, row.warehouse, 
				row.parenttype, row.name, row.item_row, stock_ledger_entries, item_sales_bom_map)
		else:
			buying_amount = get_buying_amount(row.parenttype, row.name, row.item_row,
				stock_ledger_entries.get((row.item_code, row.warehouse), []))
		
		buying_amount = buying_amount > 0 and buying_amount or 0

		gross_profit = selling_amount - buying_amount
		if selling_amount:
			gross_profit_percent = (gross_profit / selling_amount) * 100.0
		else:
			gross_profit_percent = 0.0
		
		icon = """<a href="%s"><i class="icon icon-share" style="cursor: pointer;"></i></a>""" \
			% ("/".join(["#Form", row.parenttype, row.name]),)
		data.append([row.name, icon, row.posting_date, row.posting_time, row.item_code, row.item_name,
			row.description, row.warehouse, row.qty, row.basic_rate, 
			row.qty and (buying_amount / row.qty) or 0, row.amount, buying_amount,
			gross_profit, gross_profit_percent, row.project])
			
	return columns, data
	
def get_stock_ledger_entries(filters):	
	query = """select item_code, voucher_type, voucher_no,
		voucher_detail_no, posting_date, posting_time, stock_value,
		warehouse, actual_qty as qty
		from `tabStock Ledger Entry`"""
	
	if filters.get("company"):
		query += """ where company=%(company)s"""
	
	query += " order by item_code desc, warehouse desc, posting_date desc, posting_time desc, name desc"
	
	res = webnotes.conn.sql(query, filters, as_dict=True)
	
	out = {}
	for r in res:
		if (r.item_code, r.warehouse) not in out:
			out[(r.item_code, r.warehouse)] = []
		
		out[(r.item_code, r.warehouse)].append(r)

	return out
	
def get_item_sales_bom():
	item_sales_bom = {}
	
	for d in webnotes.conn.sql("""select parenttype, parent, parent_item,
		item_code, warehouse, -1*qty as total_qty, parent_detail_docname
		from `tabPacked Item` where docstatus=1""", as_dict=True):
		item_sales_bom.setdefault(d.parenttype, webnotes._dict()).setdefault(d.parent,
			webnotes._dict()).setdefault(d.parent_item, []).append(d)

	return item_sales_bom
	
def get_source_data(filters):
	conditions = ""
	if filters.get("company"):
		conditions += " and company=%(company)s"
	if filters.get("from_date"):
		conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"):
		conditions += " and posting_date<=%(to_date)s"
	
	delivery_note_items = webnotes.conn.sql("""select item.parenttype, dn.name, 
		dn.posting_date, dn.posting_time, dn.project_name, 
		item.item_code, item.item_name, item.description, item.warehouse,
		item.qty, item.basic_rate, item.amount, item.name as "item_row",
		timestamp(dn.posting_date, dn.posting_time) as posting_datetime
		from `tabDelivery Note` dn, `tabDelivery Note Item` item
		where item.parent = dn.name and dn.docstatus = 1 %s
		order by dn.posting_date desc, dn.posting_time desc""" % (conditions,), filters, as_dict=1)

	sales_invoice_items = webnotes.conn.sql("""select item.parenttype, si.name, 
		si.posting_date, si.posting_time, si.project_name,
		item.item_code, item.item_name, item.description, item.warehouse,
		item.qty, item.basic_rate, item.amount, item.name as "item_row",
		timestamp(si.posting_date, si.posting_time) as posting_datetime
		from `tabSales Invoice` si, `tabSales Invoice Item` item
		where item.parent = si.name and si.docstatus = 1 %s
		and si.update_stock = 1
		order by si.posting_date desc, si.posting_time desc""" % (conditions,), filters, as_dict=1)
	
	source = delivery_note_items + sales_invoice_items
	if len(source) > len(delivery_note_items):
		source.sort(key=lambda d: d.posting_datetime, reverse=True)
	
	return source