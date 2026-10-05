import frappe
from frappe.utils import get_datetime, getdate

from erpnext.support.doctype.issue.test_issue import make_issue
from erpnext.support.report.support_hour_distribution.support_hour_distribution import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestSupportHourDistribution(ERPNextTestSuite):
	def test_issue_buckets_into_expected_time_slot(self):
		# The report buckets Issues by `creation` into 3-hour slots over the
		# from_date..to_date range. `creation` is auto-stamped on insert, so we
		# force it afterwards to a known time. 14:00 sits squarely inside the
		# "12PM - 3PM" slot (12:00:00 - 15:00:00), away from any slot boundary,
		# so the bucket assignment is unambiguous.
		report_date = getdate()
		issue = make_issue(customer="_Test Customer", index=1)
		creation = get_datetime(f"{report_date.strftime('%Y-%m-%d')} 14:00:00")
		frappe.db.set_value("Issue", issue.name, "creation", creation, update_modified=False)

		filters = frappe._dict(
			{
				"from_date": report_date,
				"to_date": report_date,
				"periodicity": "Daily",
			}
		)

		columns, data, _, chart = execute(filters)

		# Single day in range -> exactly one row.
		self.assertEqual(len(data), 1)
		row = data[0]
		self.assertEqual(row["date"], report_date)

		# Real-state check: the report must count exactly the Issues whose
		# `creation` falls in the 12PM-3PM window (inclusive `between`), which
		# now includes our seeded record. Compare against an independent count.
		slot_start = get_datetime(f"{report_date.strftime('%Y-%m-%d')} 12:00:00")
		slot_end = get_datetime(f"{report_date.strftime('%Y-%m-%d')} 15:00:00")
		expected = frappe.db.count("Issue", {"creation": ["between", [slot_start, slot_end]]})
		self.assertGreaterEqual(expected, 1)
		self.assertEqual(row["12PM - 3PM"], expected)

		# Columns: Date + 8 time slots.
		self.assertEqual(len(columns), 9)

		# Chart aggregates per-slot totals across the range; the 12PM-3PM
		# (5th) label must include our seeded record.
		labels = chart["data"]["labels"]
		values = chart["data"]["datasets"][0]["values"]
		self.assertGreaterEqual(values[labels.index("12PM - 3PM")], 1)
		self.assertEqual(row["12PM - 3PM"], values[labels.index("12PM - 3PM")])

	def test_late_evening_issues_count_in_the_last_slot(self):
		for index, time in enumerate(["22:15:00", "23:30:00", "23:59:59"]):
			make_issue_at(f"{REPORT_DATE} {time}", index)

		row = get_report_row()
		self.assertEqual(row["9PM - 12AM"], 3)

	def test_issue_on_a_slot_boundary_counts_once(self):
		make_issue_at(f"{REPORT_DATE} 03:00:00", 1)
		make_issue_at(f"{REPORT_DATE} 00:00:00", 2)

		row = get_report_row()
		self.assertEqual(row["12AM - 3AM"], 1)
		self.assertEqual(row["3AM - 6AM"], 1)


REPORT_DATE = "2001-03-04"


def make_issue_at(creation: str, index: int):
	issue = make_issue(customer="_Test Customer", index=index)
	frappe.db.set_value("Issue", issue.name, "creation", get_datetime(creation), update_modified=False)


def get_report_row() -> dict:
	filters = frappe._dict(from_date=REPORT_DATE, to_date=REPORT_DATE)
	return execute(filters)[1][0]
