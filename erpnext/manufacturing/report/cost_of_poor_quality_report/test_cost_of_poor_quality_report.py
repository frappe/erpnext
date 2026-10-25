# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils.data import add_days, add_to_date, get_datetime, now, today

from erpnext.manufacturing.doctype.job_card.mapper import make_corrective_job_card
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.cost_of_poor_quality_report.cost_of_poor_quality_report import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestCostOfPoorQualityReport(ERPNextTestSuite):
	"""A Job Card appears in this report only when it is submitted (docstatus == 1) and flagged
	as a corrective job card (is_corrective_job_card == 1). Such a card is created against a
	corrective Operation (is_corrective_operation == 1); without any corrective operation the
	report returns no rows at all."""

	def setUp(self):
		self.load_test_records("BOM")

	def create_corrective_job_card(self, hour_rate=100, time_logs=None):
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
		for start, minutes, completed_qty in time_logs or [(add_to_date(now(), hours=2), 30, 2)]:
			corrective_job_card.append(
				"time_logs",
				{
					"from_time": start,
					"to_time": add_to_date(start, minutes=minutes),
					"completed_qty": completed_qty,
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

	def test_date_filter_costs_only_the_time_inside_the_range(self):
		day = get_datetime(add_days(today(), -10))
		corrective_jc, _operation, _workstation = self.create_corrective_job_card(
			hour_rate=600,
			time_logs=[(add_to_date(day, hours=10), 30, 1), (add_to_date(day, days=3, hours=10), 90, 1)],
		)

		def costed(from_date, to_date):
			rows = self.run_report(
				company="_Test Company",
				name=corrective_jc.name,
				from_date=from_date,
				to_date=to_date,
			)
			return [(row.total_time_in_mins, row.operating_cost) for row in rows]

		self.assertEqual(costed(add_days(day, -1), add_days(day, 1)), [(30, 300)])
		self.assertEqual(costed(add_days(day, 2), add_days(day, 4)), [(90, 900)])
		self.assertEqual(costed(add_to_date(day, hours=10, minutes=15), add_days(day, 1)), [(15, 150)])

	def test_costs_of_split_ranges_add_up_to_the_whole_log(self):
		from unittest.mock import patch

		from erpnext.manufacturing.report.cost_of_poor_quality_report.cost_of_poor_quality_report import (
			clip_to_date_range,
		)

		log = frappe._dict(
			parent="JC-SPLIT", from_time="2026-01-01 10:00:00", to_time="2026-01-01 10:01:00", time_in_mins=1
		)
		total = 0
		for start, end in (("00", "20"), ("20", "40"), ("40", "60")):
			row = frappe._dict(name="JC-SPLIT", hour_rate=600)
			filters = {
				"from_date": f"2026-01-01 10:00:{start}" if start != "60" else "2026-01-01 10:01:00",
				"to_date": f"2026-01-01 10:00:{end}" if end != "60" else "2026-01-01 10:01:00",
			}
			with patch(
				"erpnext.manufacturing.report.cost_of_poor_quality_report.cost_of_poor_quality_report.frappe.get_all",
				return_value=[log],
			):
				clip_to_date_range([row], filters)
			total += row.operating_cost

		self.assertAlmostEqual(total, 10)

	def test_serial_and_batch_filters_match_physical_numbers(self):
		corrective_jc, _operation, _workstation = self.create_corrective_job_card()
		item = make_item("_Test COPQ Serial Batch Item", {"has_serial_no": 1, "has_batch_no": 1})
		serial_no = frappe.get_doc(
			doctype="Serial No", item_code=item.name, serial_no="COPQ-SN-01", company="_Test Company"
		).insert()
		batch = frappe.get_doc(doctype="Batch", item=item.name, batch_id="COPQ-B-01").insert()
		corrective_jc.db_set(
			{"serial_no": serial_no.serial_no, "batch_no": batch.name, "production_item": item.name}
		)

		rows = self.run_report(company="_Test Company", serial_no=serial_no.name, batch_no=batch.name)

		self.assertEqual(
			[(row.name, row.batch_no_number) for row in rows], [(corrective_jc.name, "COPQ-B-01")]
		)

	def test_serial_filter_ignores_job_cards_of_other_items(self):
		corrective_jc, _operation, _workstation = self.create_corrective_job_card()
		other_item = make_item("_Test COPQ Other Serial Item", {"has_serial_no": 1}).name
		other_serial = frappe.get_doc(
			doctype="Serial No", item_code=other_item, serial_no="COPQ-SHARED-01", company="_Test Company"
		).insert()
		corrective_jc.db_set("serial_no", "COPQ-SHARED-01")

		self.assertEqual(self.run_report(company="_Test Company", serial_no=other_serial.name), [])

	def test_serial_filter_matches_whole_serial_nos(self):
		corrective_jc, _operation, _workstation = self.create_corrective_job_card()
		item = make_item("_Test COPQ Whole Serial Item", {"has_serial_no": 1}).name
		serial_nos = [
			frappe.get_doc(
				doctype="Serial No", item_code=item, serial_no=serial_no, company="_Test Company"
			).insert()
			for serial_no in ("COPQ_SN-1", "COPQ_SN-10")
		]
		corrective_jc.db_set({"serial_no": "COPQ_SN-10\nCOPQ_SN-2", "production_item": item})

		self.assertEqual(self.run_report(company="_Test Company", serial_no=serial_nos[0].name), [])
		self.assertEqual(
			[row.name for row in self.run_report(company="_Test Company", serial_no=serial_nos[1].name)],
			[corrective_jc.name],
		)
