# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Stock Balance and Stock Ledger after Stock Reconciliations, for every kind of item.

Each item goes through the same ledger: 10 received at 100, reconciled to 15 at 120, 3 issued,
reconciled to 5 at 110, and 2 received at 100. The balance after each step is in BALANCES.
"""

from copy import deepcopy

import frappe
from frappe import _
from frappe.utils import add_days, flt, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.report.serial_and_batch_wise_stock_balance.serial_and_batch_wise_stock_balance import (
	execute as serial_and_batch_wise_stock_balance,
)
from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance
from erpnext.stock.report.stock_balance.test_stock_balance_snapshot import execute_from_snapshot
from erpnext.stock.report.stock_ledger.stock_ledger import execute as stock_ledger
from erpnext.stock.serial_batch_bundle import get_batch_nos, get_serial_nos
from erpnext.stock.tests.test_valuation_adjustment import WAREHOUSE as ADJUSTED_WAREHOUSE
from erpnext.stock.tests.test_valuation_adjustment import (
	ValuationFixTestCase,
	get_adjustment_date,
	last_year,
)
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "Stores - _TC"
OTHER_WAREHOUSE = "Finished Goods - _TC"
GROUP_WAREHOUSE = "All Warehouses - _TC"

ITEM_TYPES = {
	"normal": {},
	"serial": {"has_serial_no": 1, "serial_no_series": "RSR-SN-.#####"},
	"batch": {"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "RSR-BT-.#####"},
	"serial and batch": {
		"has_serial_no": 1,
		"serial_no_series": "RSR-SBN-.#####",
		"has_batch_no": 1,
		"create_new_batch": 1,
		"batch_number_series": "RSR-SBT-.#####",
	},
}

STEPS = ("receipt", "first reconciliation", "issue", "second reconciliation", "last receipt")
STEP_DAYS = dict(zip(STEPS, (-10, -8, -6, -4, -2), strict=True))
BALANCES = dict(zip(STEPS, ((10, 1000), (15, 1800), (12, 1440), (5, 550), (7, 750)), strict=True))


def get_step_date(step: str, days: int = 0) -> str:
	return add_days(today(), STEP_DAYS[step] + days)


class ReconciledItem:
	"""An item taken through STEPS in one warehouse."""

	def __init__(self, item_type: str, warehouse: str = WAREHOUSE):
		self.item_type = item_type
		self.warehouse = warehouse
		self.properties = ITEM_TYPES[item_type]
		self.item_code = make_item(
			properties={"is_stock_item": 1, "valuation_method": "FIFO", **self.properties}
		).name
		self.batch_no = None
		self.serial_nos = []

	@property
	def has_serial_no(self) -> bool:
		return bool(self.properties.get("has_serial_no"))

	@property
	def has_batch_no(self) -> bool:
		return bool(self.properties.get("has_batch_no"))

	def make_ledger(self) -> "ReconciledItem":
		self.receive(10, 100, "receipt")
		self.reconcile(15, 120, "first reconciliation")
		self.issue(3, "issue")
		self.reconcile(5, 110, "second reconciliation")
		self.receive(2, 100, "last receipt")
		return self

	def receive(self, qty: float, rate: float, step: str):
		entry = make_stock_entry(
			item_code=self.item_code,
			to_warehouse=self.warehouse,
			qty=qty,
			rate=rate,
			posting_date=get_step_date(step),
		)
		bundle = entry.items[0].serial_and_batch_bundle
		if self.has_batch_no and not self.batch_no:
			self.batch_no = next(iter(get_batch_nos(bundle)))

		if self.has_serial_no:
			self.serial_nos.extend(get_serial_nos(bundle))

	def issue(self, qty: float, step: str):
		serial_nos = self.serial_nos[:qty]
		self.serial_nos = self.serial_nos[qty:]
		make_stock_entry(
			item_code=self.item_code,
			from_warehouse=self.warehouse,
			qty=qty,
			posting_date=get_step_date(step),
			serial_no="\n".join(serial_nos) if serial_nos else None,
			batch_no=self.batch_no,
			use_serial_batch_fields=1,
		)

	def reconcile(self, qty: float, rate: float, step: str):
		if self.has_serial_no:
			self.serial_nos = self.get_serial_nos_for(qty)

		create_stock_reconciliation(
			item_code=self.item_code,
			warehouse=self.warehouse,
			qty=qty,
			rate=rate,
			posting_date=get_step_date(step),
			posting_time="10:00:00",
			serial_no="\n".join(self.serial_nos) if self.serial_nos else None,
			batch_no=self.batch_no,
			use_serial_batch_fields=1,
		)

	def get_serial_nos_for(self, qty: int) -> list[str]:
		serial_nos = self.serial_nos[:qty]
		for _serial in range(qty - len(serial_nos)):
			serial_nos.append(self.make_serial_no())

		return serial_nos

	def make_serial_no(self) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": frappe.generate_hash(length=12).upper(),
					"item_code": self.item_code,
					"batch_no": self.batch_no,
					"company": COMPANY,
				}
			)
			.insert()
			.name
		)


class StockReportTestCase(ERPNextTestSuite):
	def get_stock_balance(
		self, item_code, from_date=None, to_date=None, filter_by_item=True, **filters
	) -> list:
		filters = frappe._dict(
			company=COMPANY,
			from_date=from_date or add_days(today(), -30),
			to_date=to_date or today(),
			**filters,
		)
		if filter_by_item:
			filters.item_code = [item_code]

		return [frappe._dict(row) for row in stock_balance(filters)[1] if row.get("item_code") == item_code]

	def get_stock_ledger(self, item_code, warehouse, from_date=None, to_date=None, **filters) -> list:
		filters = frappe._dict(
			company=COMPANY,
			from_date=from_date or add_days(today(), -30),
			to_date=to_date or today(),
			item_code=[item_code],
			warehouse=[warehouse],
			valuation_field_type="Currency",
			**filters,
		)
		return [frappe._dict(row) for row in stock_ledger(filters)[1]]

	def assertBalanceRow(self, row, opening, balance):
		self.assertEqual((flt(row.opening_qty), flt(row.opening_val, 2)), opening, row)
		self.assertEqual((flt(row.bal_qty), flt(row.bal_val, 2)), balance, row)
		self.assertEqual(flt(row.bal_qty), flt(row.opening_qty + row.in_qty - row.out_qty), row)
		self.assertEqual(flt(row.bal_val, 2), flt(row.opening_val + row.in_val - row.out_val, 2), row)

	def assertLedgerRows(self, rows, opening_qty, balance):
		"""Every row's balance is the one before it plus its in and out qty."""
		running_qty = opening_qty
		for row in rows:
			if row.get("item_code") == _("'Opening'"):
				self.assertEqual(flt(row.qty_after_transaction), opening_qty, row)
				continue

			running_qty += flt(row.in_qty) + flt(row.out_qty)
			self.assertEqual(flt(row.qty_after_transaction), flt(running_qty), row)

		last_row = rows[-1]
		self.assertEqual((flt(last_row.qty_after_transaction), flt(last_row.stock_value)), balance)


class TestStockBalanceAfterReconciliation(StockReportTestCase):
	def test_balance_for_each_item_type(self):
		for item_type in ITEM_TYPES:
			with self.subTest(item_type=item_type):
				item = ReconciledItem(item_type).make_ledger()
				rows = self.get_stock_balance(item.item_code, warehouse=[WAREHOUSE])

				self.assertEqual(len(rows), 1)
				self.assertBalanceRow(rows[0], (0, 0), BALANCES["last receipt"])

	def test_opening_and_balance_on_each_date(self):
		for item_type in ITEM_TYPES:
			item = ReconciledItem(item_type).make_ledger()
			for step, previous_step in zip(STEPS[1:], STEPS[:-1], strict=True):
				with self.subTest(item_type=item_type, step=step):
					(row,) = self.get_stock_balance(
						item.item_code,
						from_date=get_step_date(step),
						to_date=get_step_date(step),
						warehouse=[WAREHOUSE],
					)
					self.assertBalanceRow(row, BALANCES[previous_step], BALANCES[step])

	def test_movement_of_a_normal_item(self):
		item = ReconciledItem("normal").make_ledger()
		(row,) = self.get_stock_balance(item.item_code, warehouse=[WAREHOUSE])

		self.assertEqual((row.in_qty, row.out_qty), (17, 10))

	def test_item_and_warehouse_filters(self):
		for item_type in ITEM_TYPES:
			item = ReconciledItem(item_type).make_ledger()
			item_group = frappe.db.get_value("Item", item.item_code, "item_group")
			for filters in (
				{},
				{"warehouse": [GROUP_WAREHOUSE]},
				{"warehouse": [WAREHOUSE, OTHER_WAREHOUSE]},
				{"item_group": item_group, "warehouse": [WAREHOUSE]},
			):
				with self.subTest(item_type=item_type, filters=filters):
					(row,) = self.get_stock_balance(item.item_code, **filters)
					self.assertEqual(row.warehouse, WAREHOUSE)
					self.assertBalanceRow(row, (0, 0), BALANCES["last receipt"])

	def test_without_an_item_filter(self):
		item = ReconciledItem("batch").make_ledger()
		(row,) = self.get_stock_balance(item.item_code, filter_by_item=False, warehouse=[WAREHOUSE])

		self.assertBalanceRow(row, (0, 0), BALANCES["last receipt"])

	def test_other_warehouse_is_not_affected(self):
		for item_type in ITEM_TYPES:
			with self.subTest(item_type=item_type):
				item = ReconciledItem(item_type).make_ledger()
				other = ReconciledItem(item_type, warehouse=OTHER_WAREHOUSE)
				other.item_code = item.item_code
				other.receive(4, 100, "issue")

				rows = self.get_stock_balance(item.item_code, warehouse=[GROUP_WAREHOUSE])
				self.assertEqual(
					{row.warehouse: (row.bal_qty, row.bal_val) for row in rows},
					{WAREHOUSE: BALANCES["last receipt"], OTHER_WAREHOUSE: (4, 400)},
				)


class TestStockLedgerAfterReconciliation(StockReportTestCase):
	def test_balance_for_each_item_type(self):
		for item_type in ITEM_TYPES:
			with self.subTest(item_type=item_type):
				item = ReconciledItem(item_type).make_ledger()
				rows = self.get_stock_ledger(item.item_code, WAREHOUSE)

				self.assertLedgerRows(rows, 0, BALANCES["last receipt"])

	def test_opening_on_each_date(self):
		for item_type in ITEM_TYPES:
			item = ReconciledItem(item_type).make_ledger()
			for step, previous_step in zip(STEPS[1:], STEPS[:-1], strict=True):
				with self.subTest(item_type=item_type, step=step):
					rows = self.get_stock_ledger(
						item.item_code, WAREHOUSE, from_date=get_step_date(step), to_date=get_step_date(step)
					)
					self.assertEqual(flt(rows[0].qty_after_transaction), BALANCES[previous_step][0])
					self.assertEqual(flt(rows[0].stock_value), BALANCES[previous_step][1])
					self.assertLedgerRows(rows, BALANCES[previous_step][0], BALANCES[step])

	def test_movement_of_a_normal_item(self):
		item = ReconciledItem("normal").make_ledger()
		rows = self.get_stock_ledger(item.item_code, WAREHOUSE)[1:]

		self.assertEqual([row.in_qty for row in rows], [10, 5, 0, 0, 2])
		self.assertEqual([row.out_qty for row in rows], [0, 0, -3, -7, 0])
		self.assertEqual([row.qty_after_transaction for row in rows], [10, 15, 12, 5, 7])

	def test_group_warehouse_filter(self):
		for item_type in ITEM_TYPES:
			with self.subTest(item_type=item_type):
				item = ReconciledItem(item_type).make_ledger()
				rows = self.get_stock_ledger(item.item_code, GROUP_WAREHOUSE)

				self.assertLedgerRows(rows, 0, BALANCES["last receipt"])

	def test_segregated_serial_and_batch_rows(self):
		for item_type in ("serial", "batch", "serial and batch"):
			with self.subTest(item_type=item_type):
				item = ReconciledItem(item_type).make_ledger()
				rows = self.get_stock_ledger(item.item_code, WAREHOUSE, segregate_serial_batch_bundle=1)

				self.assertLedgerRows(rows, 0, BALANCES["last receipt"])

	def test_batch_filter(self):
		for item_type in ("batch", "serial and batch"):
			for segregate in (0, 1):
				with self.subTest(item_type=item_type, segregate=segregate):
					item = ReconciledItem(item_type).make_ledger()
					rows = self.get_stock_ledger(
						item.item_code,
						WAREHOUSE,
						batch_no=item.batch_no,
						segregate_serial_batch_bundle=segregate,
					)

					self.assertEqual(flt(rows[-1].qty_after_transaction), 5)
					self.assertEqual(flt(rows[-1].stock_value), 550)


class TestReconciliationOfTwoWarehouses(StockReportTestCase):
	"""One reconciliation that raises the stock in one warehouse and lowers it in another."""

	def setUp(self):
		self.item_code = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		for warehouse, qty in ((WAREHOUSE, 10), (OTHER_WAREHOUSE, 4)):
			make_stock_entry(
				item_code=self.item_code,
				to_warehouse=warehouse,
				qty=qty,
				rate=100,
				posting_date=get_step_date("receipt"),
			)

		reconciliation = create_stock_reconciliation(
			item_code=self.item_code,
			warehouse=WAREHOUSE,
			qty=15,
			rate=100,
			posting_date=get_step_date("first reconciliation"),
			do_not_save=True,
		)
		reconciliation.append(
			"items",
			{"item_code": self.item_code, "warehouse": OTHER_WAREHOUSE, "qty": 2, "valuation_rate": 100},
		)
		reconciliation.submit()

	def test_stock_balance(self):
		item_group = frappe.db.get_value("Item", self.item_code, "item_group")
		for filters in (
			{},
			{"warehouse": [GROUP_WAREHOUSE]},
			{"filter_by_item": False, "item_group": item_group, "warehouse": [WAREHOUSE, OTHER_WAREHOUSE]},
		):
			with self.subTest(filters=filters):
				rows = self.get_stock_balance(
					self.item_code, from_date=get_step_date("first reconciliation"), **filters
				)
				self.assertEqual(
					{row.warehouse: (row.opening_qty, row.in_qty, row.out_qty, row.bal_qty) for row in rows},
					{WAREHOUSE: (10, 5, 0, 15), OTHER_WAREHOUSE: (4, 0, 2, 2)},
				)

	def test_stock_ledger_without_a_warehouse_filter(self):
		filters = frappe._dict(
			company=COMPANY,
			from_date=get_step_date("first reconciliation"),
			to_date=today(),
			item_code=[self.item_code],
			valuation_field_type="Currency",
		)
		rows = stock_ledger(filters)[1]

		self.assertEqual(
			{row["warehouse"]: (row["in_qty"], row["out_qty"], row["qty_after_transaction"]) for row in rows},
			{WAREHOUSE: (5, 0, 15), OTHER_WAREHOUSE: (0, -2, 2)},
		)


ADJUSTMENT_SCENARIOS = {
	"make_fifo_issue_at_wrong_value": {
		"stock_balance_opening": (16, 2050),
		"stock_ledger_opening": (16, 2050),
		"balance": (14, 1900),
	},
	"make_wrong_balance_qty": {
		"stock_balance_opening": (6, 700),
		"stock_ledger_opening": (7, 700),
		"balance": (6, 600),
	},
	"make_batch_issued_at_wrong_value": {
		"stock_balance_opening": (6, 700),
		"stock_ledger_opening": (6, 700),
		"balance": (5, 500),
	},
	"make_serial_no_issued_at_wrong_value": {
		"stock_balance_opening": (3, 450),
		"stock_ledger_opening": (3, 450),
		"balance": (3, 500),
	},
	"make_serial_no_counted_twice": {
		"stock_balance_opening": (4, 400),
		"stock_ledger_opening": (4, 400),
		"balance": (2, 200),
	},
}


class TestStockReportsAfterAnAdjustmentEntry(ValuationFixTestCase, StockReportTestCase):
	"""A wrong ledger set right by an Adjustment Entry. Stock Balance sums the movements for the
	opening, while Stock Ledger shows the balance of the last entry, which a wrong ledger may not
	agree with. After the Adjustment Entry both show the balance it sets."""

	def make_adjusted_ledgers(self):
		for scenario, expected in ADJUSTMENT_SCENARIOS.items():
			item_code = getattr(self, scenario)()
			self.fix_by_adjustment_entry(item_code)
			yield scenario, item_code, frappe._dict(expected)

	def test_stock_balance(self):
		for scenario, item_code, expected in self.make_adjusted_ledgers():
			for filters in ({}, {"show_dimension_wise_stock": 1}):
				with self.subTest(scenario=scenario, filters=filters):
					(row,) = self.get_stock_balance(
						item_code, from_date=get_adjustment_date(), warehouse=[ADJUSTED_WAREHOUSE], **filters
					)
					self.assertBalanceRow(row, expected.stock_balance_opening, expected.balance)

	def test_stock_balance_after_the_adjustment_date(self):
		for scenario, item_code, expected in self.make_adjusted_ledgers():
			with self.subTest(scenario=scenario):
				(row,) = self.get_stock_balance(
					item_code, from_date=add_days(today(), 1), warehouse=[ADJUSTED_WAREHOUSE]
				)
				self.assertBalanceRow(row, expected.balance, expected.balance)

	def test_stock_ledger(self):
		for scenario, item_code, expected in self.make_adjusted_ledgers():
			with self.subTest(scenario=scenario):
				rows = self.get_stock_ledger(item_code, ADJUSTED_WAREHOUSE, from_date=get_adjustment_date())
				opening_qty, opening_value = expected.stock_ledger_opening
				self.assertEqual(
					(rows[0].qty_after_transaction, rows[0].stock_value), (opening_qty, opening_value)
				)
				self.assertLedgerRows(rows, opening_qty, expected.balance)

	def test_stock_balance_snapshot(self):
		for scenario, item_code, _expected in self.make_adjusted_ledgers():
			with self.subTest(scenario=scenario):
				filters = frappe._dict(
					company=COMPANY,
					from_date=get_adjustment_date(),
					to_date=today(),
					item_code=[item_code],
					warehouse=[ADJUSTED_WAREHOUSE],
				)
				self.assertEqual(execute_from_snapshot(filters), stock_balance(deepcopy(filters)))

	def test_segregated_stock_ledger(self):
		for scenario, item_code, expected in self.make_adjusted_ledgers():
			with self.subTest(scenario=scenario):
				rows = self.get_stock_ledger(
					item_code,
					ADJUSTED_WAREHOUSE,
					from_date=get_adjustment_date(),
					segregate_serial_batch_bundle=1,
				)
				self.assertLedgerRows(rows, expected.stock_ledger_opening[0], expected.balance)

	def test_stock_ledger_with_the_batch_filter(self):
		item_code = self.make_batch_issued_at_wrong_value()
		self.fix_by_adjustment_entry(item_code)
		batch_no = frappe.db.get_value("Batch", {"item": item_code}, "name")

		for segregate in (0, 1):
			with self.subTest(segregate=segregate):
				rows = self.get_stock_ledger(
					item_code,
					ADJUSTED_WAREHOUSE,
					from_date=get_adjustment_date(),
					batch_no=batch_no,
					segregate_serial_batch_bundle=segregate,
				)
				self.assertEqual((rows[0].qty_after_transaction, rows[0].stock_value), (6, 600))
				self.assertEqual((rows[-1].qty_after_transaction, rows[-1].stock_value), (5, 500))

	def make_wrong_batch_balance_qty(self) -> str:
		"""The issue of 4 from a batch left a balance of 7 at 700 behind, where 6 at 600 are on hand."""
		item = self.make_batch_item("RSR-WBQ-.#####")
		batch_no = self.receive_batch(item, 10, 100, last_year(60))
		issue = make_stock_entry(
			item_code=item, source=ADJUSTED_WAREHOUSE, qty=4, batch_no=batch_no, posting_date=last_year(50)
		)
		self.corrupt_entry(issue.name, qty_after_transaction=7, stock_value=700, stock_value_difference=-300)
		return item

	def test_serial_and_batch_wise_stock_balance(self):
		"""The item row shows the balance the Adjustment Entry sets, as its batch rows do."""
		for scenario, balance in (
			("make_wrong_batch_balance_qty", (6, 600)),
			("make_batch_issued_at_wrong_value", (5, 500)),
		):
			item_code = getattr(self, scenario)()
			self.fix_by_adjustment_entry(item_code)
			with self.subTest(scenario=scenario):
				filters = frappe._dict(
					company=COMPANY,
					from_date=get_adjustment_date(),
					to_date=today(),
					item_code=[item_code],
					warehouse=[ADJUSTED_WAREHOUSE],
				)
				item_row, *batch_rows = (
					frappe._dict(row) for row in serial_and_batch_wise_stock_balance(filters)[1]
				)
				self.assertEqual((flt(item_row.bal_qty), flt(item_row.bal_val, 2)), balance)
				self.assertEqual(
					(
						sum(flt(row.bal_qty) for row in batch_rows),
						sum(flt(row.bal_val, 2) for row in batch_rows),
					),
					balance,
				)
