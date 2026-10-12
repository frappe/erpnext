# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import (
	get_capacity_planning_days,
)
from erpnext.manufacturing.scheduling import plan_adapter
from erpnext.tests.utils import ERPNextTestSuite


class TestManufacturingSettings(ERPNextTestSuite):
	def test_empty_capacity_planning_days_uses_one_default(self):
		frappe.db.set_single_value("Manufacturing Settings", "capacity_planning_for_days", 0)
		self.assertEqual(get_capacity_planning_days(), 30)

		with (
			patch.object(plan_adapter, "SchedulingEngine", side_effect=RuntimeError) as engine,
			patch.object(plan_adapter, "build_plan_tasks", return_value=([], {})),
			patch.object(plan_adapter.loaders, "get_workstation_resources", return_value=[]),
		):
			self.assertRaises(
				RuntimeError, plan_adapter.run_engine, frappe._dict(name="_Test Plan"), "2031-01-06"
			)
		self.assertEqual(engine.call_args.kwargs["horizon_days"], 30)

		settings = frappe.get_doc("Manufacturing Settings")
		settings.capacity_planning_for_days = 0
		settings.save()
		self.assertEqual(settings.capacity_planning_for_days, 30)
