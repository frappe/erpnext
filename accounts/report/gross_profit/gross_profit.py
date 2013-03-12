from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from stock.utils import get_buying_amount, get_sales_bom

def execute(filters=None):
	if not filters: filters = {}
	
	stock_ledger_entries = get_stock_ledger_entries(filters)
	item_sales_bom = get_sales_bom()
	
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
		buying_amount = get_buying_amount(row.item_code, row.warehouse, 
			row.qty, "Delivery Note", row.name, row.item_row, stock_ledger_entries, item_sales_bom)
		if selling_amount:
			gross_profit = selling_amount - buying_amount
			gross_profit_percent = (gross_profit / selling_amount) * 100.0
		else:
			gross_profit = gross_profit_percent = 0.0
		
		data.append([row.name, row.posting_date, row.posting_time, row.item_code, row.item_name,
			row.description, row.warehouse, row.qty, row.basic_rate, row.amount, buying_amount,
			gross_profit, gross_profit_percent, row.project])
			
	return columns, data
	
def get_stock_ledger_entries(filters):	
	query = """select item_code, voucher_type, voucher_no,
		voucher_detail_no, posting_date, posting_time, stock_value,
		warehouse, actual_qty as qty
		from `tabStock Ledger Entry` where ifnull(`is_cancelled`, "No") = "No" """
	
	if filters.get("company"):
		query += """ and company=%(company)s"""
	
	query += " order by item_code desc, warehouse desc, posting_date desc, posting_time desc, name desc"

	return webnotes.conn.sql(query, filters, as_dict=True)
