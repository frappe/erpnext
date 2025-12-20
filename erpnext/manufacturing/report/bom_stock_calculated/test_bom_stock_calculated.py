# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.tests import IntegrationTestCase

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.bom_stock_calculated.bom_stock_calculated import (
	execute as bom_stock_calculated_report,
)
from erpnext.stock.doctype.item.test_item import make_item


class TestBOMStockCalculated(IntegrationTestCase):
	def setUp(self):
		self.fg_item, self.rm_items = create_items()
		self.boms = create_boms(self.fg_item, self.rm_items)

	def test_bom_stock_calculated(self):
		qty_to_make = 10

		# Case 1: When Item(s) Qty and Stock Qty are equal.
		data = bom_stock_calculated_report(
			filters={
				"qty_to_make": qty_to_make,
				"bom": self.boms[0].name,
			}
		)[1]
		expected_data = get_expected_data(self.boms[0], qty_to_make)
		self.assertSetEqual(set(tuple(x) for x in data), set(tuple(x) for x in expected_data))

		# Case 2: When Item(s) Qty and Stock Qty are different and BOM Qty is 1.
		data = bom_stock_calculated_report(
			filters={
				"qty_to_make": qty_to_make,
				"bom": self.boms[1].name,
			}
		)[1]
		expected_data = get_expected_data(self.boms[1], qty_to_make)
		self.assertSetEqual(set(tuple(x) for x in data), set(tuple(x) for x in expected_data))

		# Case 3: When Item(s) Qty and Stock Qty are different and BOM Qty is greater than 1.
		data = bom_stock_calculated_report(
			filters={
				"qty_to_make": qty_to_make,
				"bom": self.boms[2].name,
			}
		)[1]
		expected_data = get_expected_data(self.boms[2], qty_to_make)
		self.assertSetEqual(set(tuple(x) for x in data), set(tuple(x) for x in expected_data))


def create_items():
	fg_item = make_item(properties={"is_stock_item": 1}).name
	rm_item1 = make_item(
		properties={
			"is_stock_item": 1,
			"standard_rate": 100,
			"opening_stock": 100,
			"last_purchase_rate": 100,
		}
	).name
	rm_item2 = make_item(
		properties={
			"is_stock_item": 1,
			"standard_rate": 200,
			"opening_stock": 200,
			"last_purchase_rate": 200,
		}
	).name

	return fg_item, [rm_item1, rm_item2]


def create_boms(fg_item, rm_items):
	def update_bom_items(bom, uom, conversion_factor):
		for item in bom.items:
			item.uom = uom
			item.conversion_factor = conversion_factor

		return bom

	bom1 = make_bom(item=fg_item, quantity=1, raw_materials=rm_items, rm_qty=10)

	bom2 = make_bom(item=fg_item, quantity=1, raw_materials=rm_items, rm_qty=10, do_not_submit=True)
	bom2 = update_bom_items(bom2, "Box", 10)
	bom2.save()
	bom2.submit()

	bom3 = make_bom(item=fg_item, quantity=2, raw_materials=rm_items, rm_qty=10, do_not_submit=True)
	bom3 = update_bom_items(bom3, "Box", 10)
	bom3.save()
	bom3.submit()

	return [bom1, bom2, bom3]


def get_expected_data(bom, qty_to_make):
	expected_data = []

	for idx in range(len(bom.items)):
		expected_data.append(
			[
				bom.items[idx].item_code,
				bom.items[idx].item_code,
				bom.name,
				"",
				"",
				float(bom.items[idx].stock_qty / bom.quantity),
				float(100 * (idx + 1)),
				float(qty_to_make * (bom.items[idx].stock_qty / bom.quantity)),
				float((100 * (idx + 1)) - (qty_to_make * (bom.items[idx].stock_qty / bom.quantity))),
				float(100 * (idx + 1)),
			]
		)

	return expected_data
