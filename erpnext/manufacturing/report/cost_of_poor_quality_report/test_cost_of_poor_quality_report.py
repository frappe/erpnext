# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils.data import add_to_date, now

from erpnext.manufacturing.doctype.job_card.mapper import make_corrective_job_card
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.cost_of_poor_quality_report.cost_of_poor_quality_report import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestCostOfPoorQualityReport(ERPNextTestSuite):
	"""A Job Card appears in this report only when it is submitted (docstatus == 1) and flagged
	as a corrective job card (is_corrective_job_card == 1). Such a card is created against a
	corrective Operation (is_corrective_operation == 1); without any corrective operation the
	report returns no rows at all."""

	def setUp(self):
		self.load_test_records("BOM")

	def create_corrective_job_card(self, hour_rate=100):
		"""Produce a submitted corrective Job Card and return (corrective_jc, operation, workstation)."""
		work_order = make_wo_order_test_record(item="_Test FG Item 2", qty=2)

		job_card = frappe.get_last_doc("Job Card", {"work_order": work_order.name})
		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 2},
		)
		job_card.submit()

		corrective_operation = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_operation.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = hour_rate
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=2),
				"to_time": add_to_date(now(), hours=2, minutes=30),
				"completed_qty": 2,
			},
		)
		corrective_job_card.submit()

		return corrective_job_card, corrective_operation.name, corrective_job_card.workstation

	def run_report(self, **filters):
		return execute(frappe._dict(filters))[1]

	def test_corrective_job_card_is_listed_with_expected_fields(self):
		corrective_jc, operation, workstation = self.create_corrective_job_card(hour_rate=100)

		rows = self.run_report(company="_Test Company")
		row = next((r for r in rows if r["name"] == corrective_jc.name), None)

		self.assertIsNotNone(row, "Submitted corrective job card must appear in the report")
		self.assertEqual(row["work_order"], corrective_jc.work_order)
		self.assertEqual(row["operation"], operation)
		self.assertEqual(row["workstation"], workstation)
		self.assertEqual(row["item_code"], corrective_jc.production_item)
		self.assertEqual(row["hour_rate"], 100)
		self.assertEqual(row["total_time_in_mins"], corrective_jc.total_time_in_mins)
		# operating_cost = hour_rate * total_time_in_mins / 60 (SQL float -> compare approximately)
		self.assertAlmostEqual(row["operating_cost"], 100 * corrective_jc.total_time_in_mins / 60.0, places=6)

	def test_non_corrective_job_card_is_excluded(self):
		corrective_jc, _operation, _workstation = self.create_corrective_job_card()

		# The regular (non-corrective) job card the corrective one was raised against must not appear.
		regular_jc = corrective_jc.for_job_card
		rows = self.run_report(company="_Test Company")
		self.assertNotIn(regular_jc, {r["name"] for r in rows})

	def test_operation_filter_scopes_rows(self):
		corrective_jc, operation, _workstation = self.create_corrective_job_card()

		matching = self.run_report(company="_Test Company", operation=operation)
		self.assertIn(corrective_jc.name, {r["name"] for r in matching})

		other_operation = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()
		filtered = self.run_report(company="_Test Company", operation=other_operation.name)
		self.assertNotIn(corrective_jc.name, {r["name"] for r in filtered})

	def test_workstation_filter_scopes_rows(self):
		corrective_jc, _operation, workstation = self.create_corrective_job_card()

		matching = self.run_report(company="_Test Company", workstation=workstation)
		self.assertIn(corrective_jc.name, {r["name"] for r in matching})

		filtered = self.run_report(company="_Test Company", workstation="__non_existent_ws__")
		self.assertNotIn(corrective_jc.name, {r["name"] for r in filtered})

	def test_work_order_and_name_filters_scope_rows(self):
		corrective_jc, _operation, _workstation = self.create_corrective_job_card()

		by_work_order = self.run_report(company="_Test Company", work_order=corrective_jc.work_order)
		self.assertIn(corrective_jc.name, {r["name"] for r in by_work_order})

		by_name = self.run_report(company="_Test Company", name=corrective_jc.name)
		self.assertEqual({r["name"] for r in by_name}, {corrective_jc.name})

	def test_date_filter_scopes_rows(self):
		corrective_jc, _operation, _workstation = self.create_corrective_job_card()

		# Time logs sit ~2 hours from now; a window covering today includes the card.
		within = self.run_report(
			company="_Test Company",
			work_order=corrective_jc.work_order,
			from_date=add_to_date(now(), days=-1),
			to_date=add_to_date(now(), days=1),
		)
		self.assertIn(corrective_jc.name, {r["name"] for r in within})

		# A future-only window excludes it, proving the Job Card Time Log join filters by time.
		outside = self.run_report(
			company="_Test Company",
			work_order=corrective_jc.work_order,
			from_date=add_to_date(now(), days=5),
			to_date=add_to_date(now(), days=6),
		)
		self.assertNotIn(corrective_jc.name, {r["name"] for r in outside})
