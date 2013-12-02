# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute(filters=None):
	columns = ["Date:Datetime:95", "Item:Link/Item:100", "Item Name::100", 
		"Item Group:Link/Item Group:100", "Brand:Link/Brand:100",
		"Description::200", "Warehouse:Link/Warehouse:100",
		"Stock UOM:Link/UOM:100", "Qty:Float:50", "Balance Qty:Float:80", 
		"Balance Value:Currency:100", "Voucher Type::100", "Voucher #::100",
		"Batch:Link/Batch:100", "Serial #:Link/Serial No:100", "Company:Link/Company:100"]

	data = webnotes.conn.sql("""select concat_ws(" ", posting_date, posting_time),
			item.name, item.item_name, item.item_group, brand, description, warehouse, sle.stock_uom,
			actual_qty, qty_after_transaction, stock_value, voucher_type, voucher_no, 
			batch_no, serial_no, company
		from `tabStock Ledger Entry` sle,
			(select name, item_name, description, stock_uom, brand, item_group
				from `tabItem` {item_conditions}) item
		where item_code = item.name and
			company = %(company)s and
			posting_date between %(from_date)s and %(to_date)s
			{sle_conditions}
			order by posting_date desc, posting_time desc, sle.name desc"""\
		.format(item_conditions=get_item_conditions(filters),
			sle_conditions=get_sle_conditions(filters)),
		filters)

	return columns, data
	
def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item_code=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")
	
	return "where {}".format(" and ".join(conditions)) if conditions else ""
	
def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		conditions.append("warehouse=%(warehouse)s")
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	
	return "and {}".format(" and ".join(conditions)) if conditions else ""