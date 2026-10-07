# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestItemLeadTime(ERPNextTestSuite):
	def test_scheduler_capacity_does_not_reapply_daily_yield(self):
		from erpnext.manufacturing.scheduling.plan_adapter import get_daily_capacity

		lead_time = frappe._dict(capacity_per_day=87, daily_yield=90, no_of_shift=1)
		self.assertEqual(get_daily_capacity(lead_time, None), 87)

	def make_lead_time(self, item_code, **kwargs):
		return frappe.get_doc({"doctype": "Item Lead Time", "item_code": item_code, **kwargs}).insert()

	def test_mrp_capacity_follows_renamed_item(self):
		from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
			get_item_capacity,
		)
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(properties={"is_stock_item": 1}).name
		self.make_lead_time(item_code, capacity_per_day=40)
		new_item_code = frappe.rename_doc("Item", item_code, f"{item_code}-RENAMED")

		self.assertEqual(get_item_capacity(new_item_code, "Daily"), 40)

	def test_capacity_is_computed_and_negative_times_refused(self):
		from erpnext.stock.doctype.item.test_item import make_item

		lead_time = self.make_lead_time(
			make_item(properties={"is_stock_item": 1}).name,
			shift_time_in_hours=8,
			no_of_workstations=1,
			no_of_shift=1,
			manufacturing_time_in_mins=5,
			daily_yield=90,
		)
		self.assertEqual(
			(lead_time.total_workstation_time, lead_time.no_of_units_produced, lead_time.capacity_per_day),
			(8, 96, 87),
		)

		lead_time.purchase_time = -5
		self.assertRaises(frappe.NonNegativeError, lead_time.save)

	def test_capacity_uses_unrounded_units_and_clears_with_inputs(self):
		from erpnext.stock.doctype.item.test_item import make_item

		lead_time = self.make_lead_time(
			make_item(properties={"is_stock_item": 1}).name,
			shift_time_in_hours=8,
			no_of_workstations=1,
			no_of_shift=1,
			manufacturing_time_in_mins=11,
			daily_yield=90,
		)
		self.assertEqual((lead_time.no_of_units_produced, lead_time.capacity_per_day), (43, 40))

		lead_time.no_of_workstations = 0
		lead_time.save()
		self.assertEqual(
			(lead_time.total_workstation_time, lead_time.no_of_units_produced, lead_time.capacity_per_day),
			(0, 0, 0),
		)

	def test_merging_items_with_lead_times_is_refused_cleanly(self):
		from erpnext.stock.doctype.item.test_item import make_item

		source, target = (make_item(properties={"is_stock_item": 1}).name for _i in range(2))
		for item_code in (source, target):
			self.make_lead_time(item_code, capacity_per_day=10)

		self.assertRaises(frappe.ValidationError, frappe.rename_doc, "Item", source, target, merge=True)
