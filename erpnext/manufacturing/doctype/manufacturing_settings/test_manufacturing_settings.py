# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils import flt

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_capacity_planning_days,
	get_mins_between_operations,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry as make_test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite, change_settings


class TestManufacturingSettings(ERPNextTestSuite):
	def test_empty_capacity_planning_days_uses_one_default(self):
		frappe.db.set_single_value("Manufacturing Settings", "capacity_planning_for_days", 0)
		self.assertEqual(get_capacity_planning_days(), 30)

		settings = frappe.get_doc("Manufacturing Settings")
		settings.capacity_planning_for_days = 0
		settings.save()
		self.assertEqual(settings.capacity_planning_for_days, 30)

	def test_zero_minutes_between_operations_is_kept(self):
		from erpnext.patches.v16_0.set_default_mins_between_operations import execute

		frappe.db.set_single_value("Manufacturing Settings", "mins_between_operations", 0)
		self.assertEqual(get_mins_between_operations().minutes, 0)

		execute()
		self.assertEqual(get_mins_between_operations().minutes, 10)

		frappe.db.set_single_value("Manufacturing Settings", "mins_between_operations", 0)
		self.assertEqual(get_mins_between_operations().minutes, 0)

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "BOM", "validate_components_quantities_per_bom": 1},
	)
	def test_bom_level_transferred_backflush_skips_per_bom_check(self):
		fg_item = make_item("_Test FG BOM Backflush Override", {"is_stock_item": 1}).name
		rm_item = make_item("_Test RM BOM Backflush Override", {"is_stock_item": 1}).name
		make_test_stock_entry(item_code=rm_item, target="Stores - _TC", qty=20, basic_rate=100)

		bom = make_bom(
			item=fg_item, raw_materials=[rm_item], source_warehouse="Stores - _TC", do_not_submit=True
		)
		bom.backflush_based_on = "Material Transferred for Manufacture"
		bom.submit()

		work_order = make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=10, source_warehouse="Stores - _TC"
		)
		transfer = frappe.get_doc(make_stock_entry(work_order.name, "Material Transfer for Manufacture", 10))
		transfer.items[0].qty = 12
		transfer.submit()

		manufacture = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 10))
		manufacture.submit()
		consumed = sum(row.qty for row in manufacture.items if row.item_code == rm_item)
		self.assertEqual(consumed, 12)

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "BOM", "validate_components_quantities_per_bom": 1},
	)
	def test_skip_transfer_order_keeps_per_bom_check(self):
		fg_item = make_item("_Test FG BOM Backflush Skip Transfer", {"is_stock_item": 1}).name
		rm_item = make_item("_Test RM BOM Backflush Skip Transfer", {"is_stock_item": 1}).name
		make_test_stock_entry(item_code=rm_item, target="Stores - _TC", qty=20, basic_rate=100)

		bom = make_bom(
			item=fg_item, raw_materials=[rm_item], source_warehouse="Stores - _TC", do_not_submit=True
		)
		bom.backflush_based_on = "Material Transferred for Manufacture"
		bom.submit()

		work_order = make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=10, source_warehouse="Stores - _TC", skip_transfer=1
		)
		manufacture = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 10))
		for row in manufacture.items:
			if row.item_code == rm_item:
				row.qty = flt(row.qty) + 2

		self.assertRaises(frappe.ValidationError, manufacture.submit)
