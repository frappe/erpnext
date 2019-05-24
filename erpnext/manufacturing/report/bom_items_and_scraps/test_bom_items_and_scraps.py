from __future__ import unicode_literals
import frappe, unittest
from erpnext.manufacturing.report.bom_items_and_scraps.bom_items_and_scraps import execute

class TestBomItemsAndScraps(unittest.TestCase):

	def setUp(self):
		pass

	def test_for_checking_hierarchy_of_bom_and_items_details(self):
		'''Test for checking the report records'''

		root_item = get_item("Root Item")
		item_1 = get_item("item_1")
		item_1_1 = get_item("item_1.1")
		item_1_2 = get_item("item_1.2")
		item_1_2_1 = get_item("item_1.2.1")

		bom_1_2 = get_bom(item_1_2.name, [item_1_2_1.name])
		bom_1 = get_bom(item_1.name, [item_1_1.name, item_1_2.name])
		root_bom = get_bom(root_item.name, [item_1.name])

		bom_1_2.submit()
		bom_1.submit()
		root_bom.submit()

		col, rows = execute(filters=frappe._dict({"bom": root_bom.name}))

		item_map = {}

		#Checking total no of records
		self.assertEquals(len(rows), 4)

		for row in rows:
			item_map[row['item_code']] = row

		#checking hierarchy
		self.assertEquals(item_map["item_1"]["indent"], 0)
		self.assertEquals(item_map["item_1.1"]["indent"], 1)
		self.assertEquals(item_map["item_1.2"]["indent"], 1)
		self.assertEquals(item_map["item_1.2.1"]["indent"], 2)

def get_item(item_code):

	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)

	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": item_code,
		"item_name": item_code,
		"description": item_code,
		"item_group": "Products",
		"is_stock_item": 1
	})

	if item.is_stock_item:
		for item_default in [doc for doc in item.get("item_defaults") if not doc.default_warehouse]:
			item_default.default_warehouse = "_Test Warehouse - _TC"
			item_default.company = "_Test Company"
	item.insert()

	return item

def get_bom(item_code, raw_materials):
	bom = frappe.new_doc("BOM")
	bom.item= item_code
	bom.company= "_Test Company"
	bom.quantity= 1
	bom.is_active= 1
	bom.is_default= 1
	bom.currency= "INR"

	for material in raw_materials:
		 item = {
		 	 "item_code" : material,
		 	 "qty": 2,
		 	 "uom": "Nos",
		 	 "rate": 50
		 }
		 bom.append('items', item)

	bom.insert()

	return bom