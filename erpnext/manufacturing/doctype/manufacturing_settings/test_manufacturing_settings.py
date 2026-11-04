# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_capacity_planning_days,
)


class TestManufacturingSettings(FrappeTestCase):
	def test_empty_capacity_planning_days_uses_one_default(self):
		frappe.db.set_single_value("Manufacturing Settings", "capacity_planning_for_days", 0)
		self.assertEqual(get_capacity_planning_days(), 30)

		settings = frappe.get_doc("Manufacturing Settings")
		settings.capacity_planning_for_days = 0
		settings.save()
		self.assertEqual(settings.capacity_planning_for_days, 30)
