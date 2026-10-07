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
