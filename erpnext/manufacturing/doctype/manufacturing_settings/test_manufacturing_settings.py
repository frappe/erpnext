# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_capacity_planning_days,
	get_mins_between_operations,
)


class TestManufacturingSettings(FrappeTestCase):
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
