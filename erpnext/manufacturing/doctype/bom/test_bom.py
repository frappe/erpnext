# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import cstr
from frappe.test_runner import make_test_records
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import update_cost

test_records = frappe.get_test_records('BOM')

class TestBOM(unittest.TestCase):
	def setUp(self):
		if not frappe.get_value('Item', '_Test Item'):
			make_test_records('Item')

	def test_get_items(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom=get_default_bom(),
			company="_Test Company", qty=1, fetch_exploded=0)
		self.assertTrue(test_records[2]["items"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[2]["items"][1]["item_code"] in items_dict)
		self.assertEqual(len(items_dict.values()), 2)

	def test_get_items_exploded(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom=get_default_bom(),
			company="_Test Company", qty=1, fetch_exploded=1)
		self.assertTrue(test_records[2]["items"][0]["item_code"] in items_dict)
		self.assertFalse(test_records[2]["items"][1]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["items"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["items"][1]["item_code"] in items_dict)
		self.assertEqual(len(items_dict.values()), 3)

	def test_get_items_list(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items
		self.assertEqual(len(get_bom_items(bom=get_default_bom(), company="_Test Company")), 3)

	def test_default_bom(self):
		def _get_default_bom_in_item():
			return cstr(frappe.db.get_value("Item", "_Test FG Item 2", "default_bom"))

		bom = frappe.get_doc("BOM", {"item":"_Test FG Item 2", "is_default": 1})
		self.assertEqual(_get_default_bom_in_item(), bom.name)

		bom.is_active = 0
		bom.save()
		self.assertEqual(_get_default_bom_in_item(), "")

		bom.is_active = 1
		bom.is_default=1
		bom.save()

		self.assertTrue(_get_default_bom_in_item(), bom.name)

	def test_update_bom_cost_in_all_boms(self):
		# get current rate for '_Test Item 2'
		rm_rate = frappe.db.sql("""select rate from `tabBOM Item`
			where parent='BOM-_Test Item Home Desktop Manufactured-001'
			and item_code='_Test Item 2' and docstatus=1 and parenttype='BOM'""")
		rm_rate = rm_rate[0][0] if rm_rate else 0

		# update valuation rate of item '_Test Item 2'
		warehouse_list = frappe.db.sql_list("""select warehouse from `tabBin`
			where item_code='_Test Item 2' and actual_qty > 0""")

		if not warehouse_list:
			warehouse_list.append("_Test Warehouse - _TC")

		for warehouse in warehouse_list:
			create_stock_reconciliation(item_code="_Test Item 2", warehouse=warehouse,
				qty=200, rate=rm_rate + 10)

		# update cost of all BOMs based on latest valuation rate
		update_cost()

		# check if new valuation rate updated in all BOMs
		for d in frappe.db.sql("""select rate from `tabBOM Item`
			where item_code='_Test Item 2' and docstatus=1 and parenttype='BOM'""", as_dict=1):
				self.assertEqual(d.rate, rm_rate + 10)

	def test_bom_cost(self):
		bom = frappe.copy_doc(test_records[2])
		bom.insert()

		# test amounts in selected currency
		self.assertEqual(bom.operating_cost, 100)
		self.assertEqual(bom.raw_material_cost, 8000)
		self.assertEqual(bom.total_cost, 8100)

		# test amounts in selected currency
		self.assertEqual(bom.base_operating_cost, 6000)
		self.assertEqual(bom.base_raw_material_cost, 480000)
		self.assertEqual(bom.base_total_cost, 486000)

	def test_bom_cost_multi_uom_multi_currency(self):
		frappe.db.set_value("Price List", "_Test Price List", "price_not_uom_dependant", 1)
		for item_code, rate in (("_Test Item", 3600), ("_Test Item Home Desktop Manufactured", 3000)):
			frappe.db.sql("delete from `tabItem Price` where price_list='_Test Price List' and item_code=%s",
				item_code)
			item_price = frappe.new_doc("Item Price")
			item_price.price_list = "_Test Price List"
			item_price.item_code = item_code
			item_price.price_list_rate = rate
			item_price.insert()

		bom = frappe.copy_doc(test_records[2])
		bom.set_rate_of_sub_assembly_item_based_on_bom = 0
		bom.rm_cost_as_per = "Price List"
		bom.buying_price_list = "_Test Price List"
		bom.items[0].uom = "_Test UOM 1"
		bom.items[0].conversion_factor = 5
		bom.insert()

		bom.update_cost()

		# test amounts in selected currency
		self.assertEqual(bom.items[0].rate, 300)
		self.assertEqual(bom.items[1].rate, 50)
		self.assertEqual(bom.operating_cost, 100)
		self.assertEqual(bom.raw_material_cost, 450)
		self.assertEqual(bom.total_cost, 550)

		# test amounts in selected currency
		self.assertEqual(bom.items[0].base_rate, 18000)
		self.assertEqual(bom.items[1].base_rate, 3000)
		self.assertEqual(bom.base_operating_cost, 6000)
		self.assertEqual(bom.base_raw_material_cost, 27000)
		self.assertEqual(bom.base_total_cost, 33000)

def get_default_bom(item_code="_Test FG Item 2"):
	return frappe.db.get_value("BOM", {"item": item_code, "is_active": 1, "is_default": 1})