# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.incorrect_serial_no_valuation.incorrect_serial_no_valuation import (
	execute,
	get_bundles,
	get_stock_ledger_entries,
	prepare_serial_nos,
)
from erpnext.tests.utils import ERPNextTestSuite

SERIAL_ITEM = "_Test Serialized Item With Series"
WAREHOUSE = "Stores - _TC"


class TestIncorrectSerialNoValuation(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company"})
		filters.update(extra)
		return execute(filters)[1]

	def test_healthy_serial_item_not_flagged(self):
		make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse=WAREHOUSE,
			qty=3,
			rate=100,
			posting_date="2026-06-01",
		)
		make_stock_entry(
			item_code=SERIAL_ITEM,
			from_warehouse=WAREHOUSE,
			qty=1,
			posting_date="2026-06-02",
		)

		data = self.run_report(item_code=SERIAL_ITEM)

		flagged_items = {row.get("item_code") for row in data if isinstance(row, dict)}
		self.assertNotIn(SERIAL_ITEM, flagged_items)

	def test_pre_period_receipt_is_included_when_validating_issue(self):
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "ISV-OPEN-.#####"}
		).name

		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=1, rate=100, posting_date="2026-05-31")
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=1, posting_date="2026-06-01")

		data = self.run_report(item_code=item, from_date="2026-06-01", to_date="2026-06-30")

		flagged_items = {row.get("item_code") for row in data if isinstance(row, dict)}
		self.assertNotIn(item, flagged_items)

	def test_only_balance_row_when_filtered_to_healthy_item(self):
		make_stock_entry(
			item_code=SERIAL_ITEM,
			to_warehouse=WAREHOUSE,
			qty=3,
			rate=100,
			posting_date="2026-06-01",
		)

		data = self.run_report(item_code=SERIAL_ITEM)

		# The report always appends a single "Balance" summary row. A healthy
		# serial item contributes no detail rows, so only that summary remains.
		self.assertEqual(len(data), 1)
		self.assertEqual(data[-1].get("qty"), 0)
		self.assertEqual(data[-1].get("valuation_rate"), 0)
		self.assertEqual(data[-1].serial_no_number, "Balance")
		self.assertFalse(data[-1].serial_no)

	def test_mismatched_in_out_valuation_is_flagged(self):
		self.check_mismatched_in_out_valuation("2026-06-01", "2026-06-02")

	def test_historical_discrepancy_is_excluded_from_selected_period(self):
		item, _serial_no = self.check_mismatched_in_out_valuation("2026-05-01", "2026-05-02")

		data = self.run_report(item_code=item, from_date="2026-06-01", to_date="2026-06-30")

		self.assertEqual(len(data), 1)
		self.assertEqual(data[0].serial_no_number, "Balance")
		self.assertEqual(data[0].qty, 0)
		self.assertEqual(data[0].valuation_rate, 0)

	def test_period_discrepancy_uses_opening_balance_without_showing_history(self):
		item, serial_no = self.check_mismatched_in_out_valuation("2026-05-31", "2026-06-01")

		data = self.run_report(item_code=item, from_date="2026-06-01", to_date="2026-06-30")

		details = [row for row in data if row.serial_no]
		self.assertEqual(len(details), 1)
		self.assertEqual(details[0].serial_no, serial_no)
		self.assertEqual(str(details[0].posting_date), "2026-06-01")
		self.assertEqual(data[-1].qty, 0)
		self.assertEqual(data[-1].valuation_rate, 40)

	def test_opening_history_is_limited_to_selected_serials(self):
		_item, historical_serial = self.check_mismatched_in_out_valuation("2026-05-01", "2026-05-02")
		_item, active_serial = self.check_mismatched_in_out_valuation("2026-05-31", "2026-06-01")
		filters = frappe._dict(from_date="2026-06-01", to_date="2026-06-30")

		period = get_stock_ledger_entries(filters)
		self.assertTrue(all(str(row.posting_date) >= "2026-06-01" for row in period))
		opening = get_stock_ledger_entries(filters, serial_nos=[active_serial])
		self.assertEqual(len(opening), 1)
		self.assertEqual(str(opening[0].posting_date), "2026-05-31")
		serials = prepare_serial_nos(opening, get_bundles(opening, serial_nos=[active_serial]))
		self.assertEqual(set(serials), {active_serial})
		self.assertNotIn(historical_serial, serials)

	def test_legacy_opening_rows_exclude_unselected_serials(self):
		rows = [frappe._dict(serial_nos="SERIAL-1\nSERIAL-10", actual_qty=2, valuation_rate=100)]

		serials = prepare_serial_nos(rows, {}, serial_nos=["SERIAL-1"])

		self.assertEqual(set(serials), {"SERIAL-1"})
		self.assertEqual(serials["SERIAL-1"][0].qty, 1)

	def check_mismatched_in_out_valuation(self, receipt_date, issue_date):
		# fresh serial item so only this test's serial movements are considered
		item = make_item(
			properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "ISV-BAD-.#####"}
		).name

		make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=1, rate=100, posting_date=receipt_date)
		serial_no = frappe.get_all("Serial No", filters={"item_code": item}, pluck="name")[0]
		make_stock_entry(item_code=item, from_warehouse=WAREHOUSE, qty=1, posting_date=issue_date)

		# corrupt the outgoing valuation so the serial's in (100) and out no longer cancel:
		# net qty is 0 but a residual value remains, which the report must flag
		frappe.db.set_value(
			"Serial and Batch Entry",
			{"serial_no": serial_no, "qty": ["<", 0]},
			"incoming_rate",
			60,
			update_modified=False,
		)

		data = self.run_report(item_code=item)

		flagged_serials = {row.get("serial_no") for row in data if isinstance(row, dict)}
		self.assertIn(serial_no, flagged_serials)
		serial_number = frappe.db.get_value("Serial No", serial_no, "serial_no")
		for row in data:
			if row.serial_no:
				self.assertEqual(row.serial_no_number, serial_number)
		totals = [row for row in data if row.total_label]
		self.assertEqual([row.serial_no_number for row in totals], ["Total", "Balance"])
		self.assertTrue(all(not row.serial_no for row in totals))
		return item, serial_no
