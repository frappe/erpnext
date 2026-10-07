# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestItemLeadTime(ERPNextTestSuite):
	def test_scheduler_capacity_does_not_reapply_daily_yield(self):
		from erpnext.manufacturing.scheduling.plan_adapter import get_daily_capacity

		lead_time = frappe._dict(capacity_per_day=87, daily_yield=90, no_of_shift=1)
		self.assertEqual(get_daily_capacity(lead_time, None), 87)
