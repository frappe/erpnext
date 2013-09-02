# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import webnotes

test_ignore = ["BOM"]
test_dependencies = ["Warehouse"]

class TestItem(unittest.TestCase):
	def test_duplicate_price_list(self):
		item = webnotes.bean(copy=test_records[0])
		item.doc.item_code = "_Test Item 10"
		item_price = item.doclist.get({"doctype": "Item Price"})[0]
		item.doclist.append(webnotes.doc(item_price.fields.copy()))
		self.assertRaises(webnotes.DuplicateEntryError, item.insert)

	def test_price_list_mismatch(self):
		from stock.doctype.item.item import PriceListCurrencyMismatch
		item = webnotes.bean(copy=test_records[0])
		item.doc.item_code = "_Test Item 11"
		item_price = item.doclist.get({"doctype": "Item Price"})[0].ref_currency="USD"
		self.assertRaises(PriceListCurrencyMismatch, item.insert)

	def test_default_warehouse(self):
		from stock.doctype.item.item import WarehouseNotSet
		item = webnotes.bean(copy=test_records[0])
		item.doc.is_stock_item = "Yes"
		item.doc.default_warehouse = None
		self.assertRaises(WarehouseNotSet, item.insert)

test_records = [
	[{
		"doctype": "Item",
		"item_code": "_Test Item",
		"item_name": "_Test Item",
		"description": "_Test Item",
		"item_group": "_Test Item Group",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM",
		"default_income_account": "Sales - _TC",
		"default_warehouse": "_Test Warehouse - _TC",
	}, {
		"doctype": "Item Reorder",
		"parentfield": "item_reorder",
		"warehouse": "_Test Warehouse - _TC",
		"warehouse_reorder_level": 20,
		"warehouse_reorder_qty": 20,
		"material_request_type": "Purchase"
	}, {
		"doctype": "Item Price",
		"parentfield": "ref_rate_details",
		"price_list": "_Test Price List",
		"ref_rate": 100,
		"ref_currency": "INR",
		"buying_or_selling": "Selling"
	}
	],
	[{
		"doctype": "Item",
		"item_code": "_Test Item Home Desktop 100",
		"item_name": "_Test Item Home Desktop 100",
		"description": "_Test Item Home Desktop 100",
		"item_group": "_Test Item Group Desktops",
		"default_warehouse": "_Test Warehouse - _TC",
		"default_income_account": "Sales - _TC",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	},
	{
		"doctype": "Item Tax",
		"tax_type": "_Test Account Excise Duty - _TC",
		"tax_rate": 10
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Item Home Desktop 200",
		"item_name": "_Test Item Home Desktop 200",
		"description": "_Test Item Home Desktop 200",
		"item_group": "_Test Item Group Desktops",
		"default_warehouse": "_Test Warehouse - _TC",
		"default_income_account": "Sales - _TC",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Sales BOM Item",
		"item_name": "_Test Sales BOM Item",
		"description": "_Test Sales BOM Item",
		"item_group": "_Test Item Group Desktops",
		"default_income_account": "Sales - _TC",
		"is_stock_item": "No",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test FG Item",
		"item_name": "_Test FG Item",
		"description": "_Test FG Item",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"default_warehouse": "_Test Warehouse - _TC",
		"default_income_account": "Sales - _TC",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "Yes",
		"is_sub_contracted_item": "Yes",
		"stock_uom": "_Test UOM"
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Non Stock Item",
		"item_name": "_Test Non Stock Item",
		"description": "_Test Non Stock Item",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "No",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Serialized Item",
		"item_name": "_Test Serialized Item",
		"description": "_Test Serialized Item",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"default_warehouse": "_Test Warehouse - _TC",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "Yes",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Serialized Item With Series",
		"item_name": "_Test Serialized Item With Series",
		"description": "_Test Serialized Item",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"default_warehouse": "_Test Warehouse - _TC",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "Yes",
		"serial_no_series": "ABCD.#####",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
]