# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.utils import fmt_money

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.bom_stock_analysis.bom_stock_analysis import (
	execute as bom_stock_analysis_report,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


def fmt_qty(value):
	return fmt_money(value, precision=2, currency=None)


def fmt_rate(value):
	currency = frappe.defaults.get_global_default("currency")
	return fmt_money(value, precision=2, currency=currency)


class TestBOMStockAnalysis(ERPNextTestSuite):
	def setUp(self):
		self.fg_item, self.rm_items = create_items()
		self.boms = create_boms(self.fg_item, self.rm_items)

	def test_bom_stock_analysis(self):
		qty_to_make = 10

		# Case 1: When Item(s) Qty and Stock Qty are equal.
		raw_data = bom_stock_analysis_report(
			filters={
				"qty_to_make": qty_to_make,
				"bom": self.boms[0].name,
			}
		)[1]

		data, footer = split_data_and_footer(raw_data)
		expected_data, expected_min = get_expected_data(self.boms[0], qty_to_make)

		self.assertSetEqual(
			set(tuple(sorted(r.items())) for r in data),
			set(tuple(sorted(r.items())) for r in expected_data),
		)
		self.assertEqual(footer.get("description"), expected_min)

		# Case 2: When Item(s) Qty and Stock Qty are different and BOM Qty is 1.
		raw_data = bom_stock_analysis_report(
			filters={
				"qty_to_make": qty_to_make,
				"bom": self.boms[1].name,
			}
		)[1]

		data, footer = split_data_and_footer(raw_data)
		expected_data, expected_min = get_expected_data(self.boms[1], qty_to_make)

		self.assertSetEqual(
			set(tuple(sorted(r.items())) for r in data),
			set(tuple(sorted(r.items())) for r in expected_data),
		)
		self.assertEqual(footer.get("description"), expected_min)

		# Case 3: When Item(s) Qty and Stock Qty are different and BOM Qty is greater than 1.
		raw_data = bom_stock_analysis_report(
			filters={
				"qty_to_make": qty_to_make,
				"bom": self.boms[2].name,
			}
		)[1]

		data, footer = split_data_and_footer(raw_data)
		expected_data, expected_min = get_expected_data(self.boms[2], qty_to_make)

		self.assertSetEqual(
			set(tuple(sorted(r.items())) for r in data),
			set(tuple(sorted(r.items())) for r in expected_data),
		)
		self.assertEqual(footer.get("description"), expected_min)


def split_data_and_footer(raw_data):
	"""Separate component rows from the footer row. Skips blank spacer rows."""
	data = [row for row in raw_data if row and not row.get("bold")]
	footer = next((row for row in raw_data if row and row.get("bold")), {})
	return data, footer


def create_items():
	fg_item = make_item(properties={"is_stock_item": 1}).name
	rm_item1 = make_item(
		properties={
			"is_stock_item": 1,
			"standard_rate": 100,
			"opening_stock": 100,
			"last_purchase_rate": 100,
			"item_defaults": [{"company": "_Test Company", "default_warehouse": "Stores - _TC"}],
		}
	).name
	rm_item2 = make_item(
		properties={
			"is_stock_item": 1,
			"standard_rate": 200,
			"opening_stock": 200,
			"last_purchase_rate": 200,
			"item_defaults": [{"company": "_Test Company", "default_warehouse": "Stores - _TC"}],
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
	"""
	Returns (component_rows, min_producible).
	Component rows are dicts matching what the report produces.
	min_producible is the expected footer value.
	"""
	expected_data = []
	producible_per_item = []

	for idx, bom_item in enumerate(bom.items):
		qty_per_unit = float(bom_item.stock_qty / bom.quantity)
		available_qty = float(100 * (idx + 1))
		required_qty = float(qty_to_make * qty_per_unit)
		difference_qty = available_qty - required_qty
		last_purchase_rate = float(100 * (idx + 1))

		expected_data.append(
			{
				"item": bom_item.item_code,
				"description": bom_item.item_code,  # description falls back to item_code in test items
				"from_bom_no": bom.name,
				"manufacturer": "",
				"manufacturer_part_number": "",
				"qty_per_unit": fmt_qty(qty_per_unit),
				"available_qty": fmt_qty(available_qty),
				"required_qty": fmt_qty(required_qty),
				"difference_qty": fmt_qty(difference_qty),
				"last_purchase_rate": fmt_rate(last_purchase_rate),
			}
		)

		producible_per_item.append(int(available_qty // qty_per_unit) if qty_per_unit else 0)

	min_producible = min(producible_per_item) if producible_per_item else 0

	return expected_data, min_producible
