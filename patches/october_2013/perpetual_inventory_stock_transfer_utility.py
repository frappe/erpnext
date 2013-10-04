# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import nowdate, nowtime
from accounts.utils import get_fiscal_year

def execute():
	item_map = {}
	for item in webnotes.conn.sql("""select * from tabItem""", as_dict=1):
		item_map.setdefault(item.name, item)
	
	warehouse_map = get_warehosue_map()
	# naming_series = 
	for company in webnotes.conn.sql("select name from tabCompany"):
		stock_entry = [{
			"doctype": "Stock Entry",
			"naming_series": naming_series,
			"posting_date": nowdate(),
			"posting_time": nowtime(),
			"purpose": "Material Transfer",
			"company": company[0],
			"remarks": "Material Transfer to activate perpetual inventory",
			"fiscal_year": get_fiscal_year(nowdate())
		}]
		expense_account = "Cost of Goods Sold - NISL"
		cost_center = "Default CC Ledger - NISL"
		
		for bin in webnotes.conn.sql("select * from tabBin where company=%s", company[0] as_dict=1):
			new_warehouse = warehouse_map[bin.warehouse].get("fixed_asset_warehouse") \
				if cstr(item_map[bin.item_code]) == "Yes" else wh.get("current_asset_warehouse")
			
			item_details = item_map[bin.item_code]
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
				"cost_center": cost_center
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
		"ASSET-MAHAPE": {
			"current_asset_warehouse": "",
			"fixed_asset_warehouse": "Assets-New - NISL"
		}
	}