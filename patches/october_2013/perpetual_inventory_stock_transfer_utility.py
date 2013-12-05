# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import nowdate, nowtime, cstr
from accounts.utils import get_fiscal_year

def execute():
	item_map = {}
	for item in webnotes.conn.sql("""select * from tabItem""", as_dict=1):
		item_map.setdefault(item.name, item)
	
	warehouse_map = get_warehosue_map()
	naming_series = "STE/13/"
	
	for company in webnotes.conn.sql("select name from tabCompany"):
		stock_entry = [{
			"doctype": "Stock Entry",
			"naming_series": naming_series,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"purpose": "Material Transfer",
			"company": company[0],
			"remarks": "Material Transfer to activate perpetual inventory",
			"fiscal_year": get_fiscal_year(nowdate())[0]
		}]
		expense_account = "Cost of Goods Sold - NISL"
		cost_center = "Default CC Ledger - NISL"
		
		for bin in webnotes.conn.sql("""select * from tabBin bin where ifnull(item_code, '')!='' 
				and ifnull(warehouse, '') in (%s) and ifnull(actual_qty, 0) != 0
				and (select company from tabWarehouse where name=bin.warehouse)=%s""" %
				(', '.join(['%s']*len(warehouse_map)), '%s'), 
				(warehouse_map.keys() + [company[0]]), as_dict=1):
			item_details = item_map[bin.item_code]
			new_warehouse = warehouse_map[bin.warehouse].get("fixed_asset_warehouse") \
				if cstr(item_details.is_asset_item) == "Yes" \
				else warehouse_map[bin.warehouse].get("current_asset_warehouse")
				
			if item_details.has_serial_no == "Yes":
				serial_no = "\n".join([d[0] for d in webnotes.conn.sql("""select name 
					from `tabSerial No` where item_code = %s and warehouse = %s 
					and status in ('Available', 'Sales Returned')""", 
					(bin.item_code, bin.warehouse))])
			else:
				serial_no = None
			
			stock_entry.append({
				"doctype": "Stock Entry Detail",
				"parentfield": "mtn_details",
				"s_warehouse": bin.warehouse,
				"t_warehouse": new_warehouse,
				"item_code": bin.item_code,
				"description": item_details.description,
				"qty": bin.actual_qty,
				"transfer_qty": bin.actual_qty,
				"uom": item_details.stock_uom,
				"stock_uom": item_details.stock_uom,
				"conversion_factor": 1,
				"expense_account": expense_account,
				"cost_center": cost_center,
				"serial_no": serial_no
			})
		
		webnotes.bean(stock_entry).insert()
		
def get_warehosue_map():
	return {
		"MAHAPE": {
			"current_asset_warehouse": "Mahape-New - NISL",
			"fixed_asset_warehouse": ""
		},
		"DROP SHIPMENT": {
			"current_asset_warehouse": "Drop Shipment-New - NISL",
			"fixed_asset_warehouse": ""
		},
		"TRANSIT": {
			"current_asset_warehouse": "Transit-New - NISL",
			"fixed_asset_warehouse": ""
		},
		"ASSET - MAHAPE": {
			"current_asset_warehouse": "",
			"fixed_asset_warehouse": "Assets-New - NISL"
		}
	}