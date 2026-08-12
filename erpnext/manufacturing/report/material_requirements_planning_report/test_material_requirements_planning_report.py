# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.classes.context_managers import freeze_time
from frappe.utils import add_days, formatdate, today

from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
	MaterialRequirementsPlanningReport,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestMaterialRequirementsPlanningReport(ERPNextTestSuite):
	def test_detailed_chart_includes_full_date_range(self):
		with freeze_time("2026-08-12"):
			start_date = add_days(today(), 1)
			delivery_dates = [add_days(start_date, offset) for offset in range(12)]
			rows = [make_chart_row(delivery_date) for delivery_date in delivery_dates]
			rows.append(make_chart_row(delivery_dates[-1], planned_qty=2))

			chart = MaterialRequirementsPlanningReport(frappe._dict()).get_detailed_view_chart_data(rows)

			self.assertEqual(
				chart["data"]["labels"],
				[formatdate(delivery_date, "dd MMM") for delivery_date in delivery_dates],
			)
			self.assertEqual(chart["data"]["datasets"][0]["values"], [1] * 11 + [3])

	def test_detailed_chart_distinguishes_delivery_dates_across_years(self):
		with freeze_time("2026-08-12"):
			delivery_dates = ["2026-08-15", "2027-08-15"]
			rows = [
				make_chart_row(delivery_dates[0]),
				make_chart_row(delivery_dates[1], planned_qty=2),
			]

			chart = MaterialRequirementsPlanningReport(frappe._dict()).get_detailed_view_chart_data(rows)

			self.assertEqual(
				chart["data"]["labels"],
				[formatdate(delivery_date, "dd MMM yyyy") for delivery_date in delivery_dates],
			)
			self.assertEqual(chart["data"]["datasets"][0]["values"], [1, 2])

	def test_detailed_chart_excludes_past_and_empty_delivery_dates(self):
		with freeze_time("2026-08-12"):
			delivery_dates = [today(), add_days(today(), 1)]
			rows = [
				make_chart_row(add_days(today(), -1)),
				make_chart_row(None),
				*[make_chart_row(delivery_date) for delivery_date in delivery_dates],
			]

			chart = MaterialRequirementsPlanningReport(frappe._dict()).get_detailed_view_chart_data(rows)

			self.assertEqual(
				chart["data"]["labels"],
				[formatdate(delivery_date, "dd MMM") for delivery_date in delivery_dates],
			)


def make_chart_row(delivery_date, planned_qty=1):
	return frappe._dict(
		{
			"delivery_date": delivery_date,
			"planned_qty": planned_qty,
			"in_hand_qty": 0,
			"po_ordered_qty": 0,
			"wo_ordered_qty": 0,
		}
	)
