from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

stock_ledger_entries = None
item_sales_bom = None

def execute(filters=None):
	if not filters: filters = {}
	
	get_stock_ledger_entries(filters)
	get_sales_bom()
	
	delivery_note_items = webnotes.conn.sql("""select dn.name, dn.posting_date, dn.posting_time,
		dn.project_name, item.item_code, item.item_name, item.description, item.warehouse,
		item.qty, item.basic_rate, item.amount, item.name as "item_row"
		from `tabDelivery Note` dn, `tabDelivery Note Item` item
		where item.parent = dn.name and dn.docstatus = 1
		order by dn.posting_date desc, dn.posting_time desc""", as_dict=1)
	
	columns = ["Delivery Note:Link/Delivery Note", "Posting Date:Date", "Posting Time", 
		"Item Code:Link/Item", "Item Name", "Description", "Warehouse:Link/Warehouse",
		"Qty:Float", "Selling Rate:Currency", "Selling Amount:Currency", "Buying Amount:Currency",
		"Gross Profit:Currency", "Gross Profit %:Percent", "Project:Link/Project"]
		
	data = []
	for row in delivery_note_items:
		selling_amount = flt(row.amount)
		buying_amount = get_buying_amount(row)
		if selling_amount:
			gross_profit = selling_amount - buying_amount
			gross_profit_percent = (gross_profit / selling_amount) * 100.0
		else:
			gross_profit = gross_profit_percent = 0.0
		
		data.append([row.name, row.posting_date, row.posting_time, row.item_code, row.item_name,
			row.description, row.warehouse, row.qty, row.basic_rate, row.amount, buying_amount,
			gross_profit, gross_profit_percent, row.project])
			
	return columns, data

def get_buying_amount(row):
	if item_sales_bom.get(row.item_code):
		# sales bom item
		buying_amount = 0.0
		for bom_item in item_sales_bom[row.item_code]:
			buying_amount += _get_buying_amount(row.name, "[** No Item Row **]",
				bom_item.item_code, row.warehouse, bom_item.qty * row.qty)
		return buying_amount
	else:
		# doesn't have sales bom
		return _get_buying_amount(row.name, row.item_row, row.item_code, row.warehouse, row.qty)
		
def _get_buying_amount(voucher_no, item_row, item_code, warehouse, qty):
	for i, sle in enumerate(stock_ledger_entries):
		if sle.voucher_type == "Delivery Note" and sle.voucher_no == voucher_no:
			if (sle.voucher_detail_no == item_row) or \
				(sle.item_code == item_code and sle.warehouse == warehouse and \
				abs(flt(sle.qty)) == qty):
					buying_amount = flt(stock_ledger_entries[i+1].stock_value) - flt(sle.stock_value)

					return buying_amount
					
	return 0.0

def get_sales_bom():
	global item_sales_bom
	
	item_sales_bom = {}
	
	for r in webnotes.conn.sql("""select parent, item_code, qty from `tabSales BOM Item`""", as_dict=1):
		item_sales_bom.setdefault(r.parent, []).append(r)
	
def get_stock_ledger_entries(filters):
	global stock_ledger_entries
	
	query = """select item_code, voucher_type, voucher_no,
		voucher_detail_no, posting_date, posting_time, stock_value,
		warehouse, actual_qty as qty
		from `tabStock Ledger Entry` where ifnull(`is_cancelled`, "No") = "No" """
	
	if filters.get("company"):
		query += """ and company=%(company)s"""
	
	query += " order by item_code desc, warehouse desc, posting_date desc, posting_time desc, name desc"

	stock_ledger_entries = webnotes.conn.sql(query, filters, as_dict=True)
