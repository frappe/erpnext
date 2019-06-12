from __future__ import unicode_literals
import frappe, unittest
from erpnext.stock.report.stock_balance.stock_balance import execute
from frappe.utils import now, add_to_date

class TestStockBalance(unittest.TestCase):

	def test_for_stock_balance_with_date_filter(self):
		item_1 = get_item("Test_Mac_Book_Pro", 12345)
		item_2 = get_item("Test_One_Plus", 6789)

		cols, rows = execute(filters=frappe._dict({"from_date": now(), "to_date": add_to_date(now(), months = 1)}))

		from pprint import pprint
		pprint(rows)

		item_map = get_item_map(rows)

		self.assertEquals(item_map['Test_One_Plus'][11],6789.0)
		self.assertEquals(item_map['Test_Mac_Book_Pro'][11],12345.0)

	def test_for_stock_balance_with_warehouse_and_warehouse_type(self):

		item_1 = get_item("Test_item_for_warehouse_type", 2367)

		wt = get_warehouse_type()

		warehouse = frappe.get_doc("Warehouse", item_1.item_defaults[0].default_warehouse)
		warehouse.warehouse_type = wt.name
		warehouse.save()

		cols, rows = execute(filters=frappe._dict({
				"from_date": now(),
				"to_date": add_to_date(now(), months = 1),
				"warehouse_type": wt.name
			}))

		item_map = get_item_map(rows)

		self.assertEquals(item_map['Test_item_for_warehouse_type'][5], item_1.item_defaults[0].default_warehouse)
		self.assertEquals(item_map['Test_item_for_warehouse_type'][11], 2367)

def get_item_map(rows):

	item_map = {}
	for row in rows:
		item_map[row[0]] = row

	return item_map


def get_item(item_code, qty):

	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)
	else:
		item = frappe.new_doc("Item")
		item.item_name = item_code
		item.item_code = item_code
		item.item_group = "All Item Groups"
		item.valuation_rate = 10.0
		item.stock_uom = "_Test UOM"
		item.opening_stock = qty
		item.is_stock_item = 1

		item.insert()

def get_warehouse_type():

	if frappe.db.exists("Warehouse Type", "Reserved"):
		return frappe.get_doc("Warehouse Type", "Reserved")

	wt = frappe.get_doc({
			"doctype": "Warehouse Type",
			"name": "Reserved"
		})

	return wt