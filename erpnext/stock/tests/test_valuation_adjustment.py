# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Wrong ledgers, found by the Stock Valuation Comparison report and set right from it.

Each scenario leaves a ledger the way a valuation bug would, in a past fiscal year: an entry
carrying a value or a balance it should not, with stock moving on after it. Every scenario is then
set right twice, in separate tests:

* by a repost from the report, which rewrites the past fiscal year;
* by an Adjustment Entry on the first day of the current fiscal year, which leaves the past fiscal
  year as it was filed and sets stock and accounts right from its date on.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, flt, getdate, nowdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost as run_repost
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots
from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance
from erpnext.stock.report.stock_ledger_entries_of_cancelled_vouchers.test_stock_ledger_entries_of_cancelled_vouchers import (
	make_stock_manager,
)
from erpnext.stock.report.stock_valuation_comparison.stock_valuation_comparison import (
	SHOW_ALL_DIFFERENCES,
	execute,
	get_repost_preview,
	make_adjustment_entry,
	make_repost_entries,
)
from erpnext.stock.report.stock_valuation_comparison.test_stock_valuation_comparison import (
	make_batch_without_batch_wise_valuation,
)
from erpnext.stock.valuation_adjustment import ADJUSTMENT_ENTRY, BackdatedEntryBeforeAdjustmentError
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"


def get_adjustment_date() -> str:
	"""The first day of the current fiscal year: everything before it is filed."""
	return str(get_fiscal_year(nowdate(), company=COMPANY)[1])


def last_year(days_before_close: int) -> str:
	return add_days(get_adjustment_date(), -days_before_close)


def this_year(days: int) -> str:
	"""A date after the adjustment, no later than today."""
	return str(min(getdate(add_days(get_adjustment_date(), days)), getdate(nowdate())))


class ValuationFixTestCase(ERPNextTestSuite):
	"""Builds the wrong ledgers, and sets them right the two ways the report offers."""

	def setUp(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)

	def run_report(self, item_code, **filters):
		return execute(
			frappe._dict(company=COMPANY, item_code=item_code, show=SHOW_ALL_DIFFERENCES, **filters)
		)[1]

	def get_differences(self, item_code) -> list[str]:
		return [row.stock_ledger_entry for row in self.run_report(item_code)]

	def corrupt_entry(self, voucher_no, item_code=None, bundle_value=None, **values) -> str:
		"""Leave wrong values on the voucher's ledger entry, and on its bundle when given."""
		filters = {"voucher_no": voucher_no, "is_cancelled": 0}
		if item_code:
			filters["item_code"] = item_code

		sle = frappe.db.get_value("Stock Ledger Entry", filters, "name")
		frappe.db.set_value("Stock Ledger Entry", sle, values, update_modified=False)

		if bundle_value is not None:
			# the bundle carries the same wrong value, and the rate it makes
			bundle = frappe.db.get_value("Stock Ledger Entry", sle, "serial_and_batch_bundle")
			entry = frappe.db.get_value(
				"Serial and Batch Entry", {"parent": bundle}, ["name", "qty"], as_dict=True
			)
			frappe.db.set_value(
				"Serial and Batch Entry",
				entry.name,
				{"stock_value_difference": bundle_value, "incoming_rate": abs(bundle_value / entry.qty)},
				update_modified=False,
			)

		return sle

	def get_ledger_before_adjustment(self, item_code) -> list[tuple]:
		return frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"item_code": item_code,
				"is_cancelled": 0,
				"posting_date": ("<", get_adjustment_date()),
			},
			fields=["name", "qty_after_transaction", "stock_value", "stock_value_difference"],
			order_by="posting_datetime, creation",
			as_list=True,
		)

	def fix_by_repost(self, item_code):
		differences = self.get_differences(item_code)
		self.assertTrue(differences, "the ledger should have been wrong")
		history = self.get_ledger_before_adjustment(item_code)

		result = make_repost_entries(COMPANY, differences)
		self.assertEqual(result["not_created"], [])

		# in tests a repost runs as soon as it is submitted
		self.assertEqual(self.run_report(item_code, show_adjusted_differences=1), [])
		# and it rewrites the past fiscal year
		self.assertNotEqual(self.get_ledger_before_adjustment(item_code), history)

	def fix_by_adjustment_entry(self, item_code):
		differences = self.get_differences(item_code)
		self.assertTrue(differences, "the ledger should have been wrong")
		history = self.get_ledger_before_adjustment(item_code)

		result = make_adjustment_entry(COMPANY, differences, get_adjustment_date(), "00:00:00")
		self.assertEqual(result["not_adjusted"], [])
		adjustment = frappe.get_doc("Stock Reconciliation", result["adjustment_entry"])
		self.assertEqual(adjustment.purpose, ADJUSTMENT_ENTRY)
		adjustment.submit()

		# from its date on the ledger is right
		self.assertEqual(self.run_report(item_code), [])

		# the past fiscal year keeps what was filed, with its differences settled by the adjustment
		self.assertEqual(self.get_ledger_before_adjustment(item_code), history)
		settled = self.run_report(item_code, show_adjusted_differences=1)
		self.assertTrue(settled)
		self.assertEqual({row.adjusted_by for row in settled}, {adjustment.name})
		self.assertTrue(all(str(row.posting_date) < get_adjustment_date() for row in settled))

		return adjustment

	def get_balance_movement(self, item_code) -> frappe._dict:
		"""What Stock Balance shows went in and out of the warehouse from the adjustment date on."""
		rows = stock_balance(
			frappe._dict(
				company=COMPANY,
				from_date=get_adjustment_date(),
				to_date=nowdate(),
				item_code=[item_code],
				warehouse=WAREHOUSE,
			)
		)[1]
		return rows[0] if rows else frappe._dict()

	def get_fifo_queue(self, item_code) -> list:
		slots = FIFOSlots(
			frappe._dict(
				company=COMPANY,
				to_date=nowdate(),
				item_code=item_code,
				warehouse=WAREHOUSE,
				ranges=["30", "60", "90"],
				show_warehouse_wise_stock=1,
			)
		).generate()
		return slots[(item_code, WAREHOUSE)]["fifo_queue"]

	# the wrong ledgers

	def make_fifo_issue_at_wrong_value(self) -> str:
		"""10 at 100 and 10 at 150 received; 4 issued at 450 instead of 400, then 2 more this year."""
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100, posting_date=last_year(60))
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=150, posting_date=last_year(55))
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=4, posting_date=last_year(50))
		self.corrupt_entry(issue.name, stock_value_difference=-450, stock_value=2050)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=2, posting_date=this_year(1))

		return item

	def make_moving_average_value_drift(self) -> str:
		"""The balance qty and rate are right, the balance value is 30 short."""
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "Moving Average"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100, posting_date=last_year(60))
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=4, posting_date=last_year(50))
		self.corrupt_entry(issue.name, stock_value_difference=-430, stock_value=570)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=1, posting_date=this_year(1))

		return item

	def make_wrong_balance_qty(self) -> str:
		"""The issue left a balance of 7 at 700 behind, where 6 at 600 are on hand."""
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, rate=100, posting_date=last_year(60))
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=4, posting_date=last_year(50))
		self.corrupt_entry(
			issue.name,
			qty_after_transaction=7,
			stock_value=700,
			stock_value_difference=-300,
			stock_queue=frappe.as_json([[7, 100]]),
		)

		return item

	def make_batch_item(self, series) -> str:
		return make_item(
			properties={
				"is_stock_item": 1,
				"valuation_method": "FIFO",
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": series,
			}
		).name

	def receive_batch(self, item, qty, rate, posting_date) -> str:
		receipt = make_purchase_receipt(
			item_code=item, warehouse=WAREHOUSE, qty=qty, rate=rate, posting_date=posting_date
		)
		return frappe.db.get_value(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, "batch_no"
		)

	def make_batch_issued_at_wrong_value(self) -> str:
		"""A batch valued batch-wise: 10 at 100 received, and the ledger entry of the issue of 4 at 300
		instead of 400."""
		item = self.make_batch_item("SVA-BWV-.#####")

		batch_no = self.receive_batch(item, 10, 100, last_year(60))
		self.assertTrue(frappe.db.get_value("Batch", batch_no, "use_batchwise_valuation"))
		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=4, batch_no=batch_no, posting_date=last_year(50)
		)
		self.corrupt_entry(issue.name, stock_value_difference=-300, stock_value=700)
		make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=1, batch_no=batch_no, posting_date=this_year(1)
		)

		return item

	def make_batch_holding_value_with_no_qty(self) -> tuple[str, str]:
		"""A batch valued batch-wise issued in full at 800 instead of 1,000: it is left with 200 and
		no qty, which the ledger would average into the next stock of the batch."""
		item = self.make_batch_item("SVA-BNQ-.#####")

		empty_batch = self.receive_batch(item, 10, 100, last_year(60))
		self.receive_batch(item, 5, 120, last_year(58))
		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=10, batch_no=empty_batch, posting_date=last_year(50)
		)
		self.corrupt_entry(issue.name, bundle_value=-800, stock_value_difference=-800, stock_value=800)

		return item, empty_batch

	def make_pooled_batches_from_wrong_layer(self) -> str:
		"""Batches valued in a FIFO pool of 10 at 100 and 10 at 150: the issue of 4 took them from
		the 150 layer instead of the oldest one."""
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO", "has_batch_no": 1}).name

		first_batch, second_batch = (make_batch_without_batch_wise_valuation(item) for _i in range(2))
		for batch_no, rate, days in ((first_batch, 100, 60), (second_batch, 150, 55)):
			make_purchase_receipt(
				item_code=item,
				warehouse=WAREHOUSE,
				qty=10,
				rate=rate,
				batch_no=batch_no,
				posting_date=last_year(days),
			)

		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=4, batch_no=second_batch, posting_date=last_year(50)
		)
		self.corrupt_entry(
			issue.name,
			bundle_value=-600,
			stock_value_difference=-600,
			stock_value=1900,
			stock_queue=frappe.as_json([[10, 100], [6, 150]]),
		)

		return item

	def make_pool_value_no_batch_holds(self) -> str:
		"""Batches valued in the pool: the stock value is 100 short, but the queue the batches are
		counted out from is right."""
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO", "has_batch_no": 1}).name

		batch_no = make_batch_without_batch_wise_valuation(item)
		make_purchase_receipt(
			item_code=item,
			warehouse=WAREHOUSE,
			qty=10,
			rate=100,
			batch_no=batch_no,
			posting_date=last_year(60),
		)
		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=4, batch_no=batch_no, posting_date=last_year(50)
		)
		self.corrupt_entry(issue.name, stock_value_difference=-500, stock_value=500)

		return item

	def make_serial_item(self, series) -> str:
		return make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": series}).name

	def make_serial_no_issued_at_wrong_value(self) -> str:
		"""2 serial nos received at 100 and 2 at 200; one of the first issued at 150."""
		item = self.make_serial_item("SVA-SR-.#####")

		receipt = make_stock_entry(
			item_code=item, target=WAREHOUSE, qty=2, rate=100, posting_date=last_year(60)
		)
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=2, rate=200, posting_date=last_year(58))
		serial_no = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, "serial_no"
		)
		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=1, serial_no=[serial_no], posting_date=last_year(50)
		)
		self.corrupt_entry(issue.name, bundle_value=-150, stock_value_difference=-150, stock_value=450)

		return item

	def make_serial_no_counted_twice(self) -> str:
		"""A receipt of 2 serial nos entered in the ledger twice, as in a copied entry: the ledger holds
		4 units, of which only 2 have a serial no."""
		item = self.make_serial_item("SVA-DUP-.#####")

		receipt = make_stock_entry(
			item_code=item, target=WAREHOUSE, qty=2, rate=100, posting_date=last_year(60)
		)
		sle = frappe.get_doc(
			"Stock Ledger Entry", {"voucher_no": receipt.name, "item_code": item, "is_cancelled": 0}
		)
		copy = frappe.copy_doc(sle)
		copy.update(
			{"name": frappe.generate_hash(length=10), "creation": add_to_date(sle.creation, seconds=-1)}
		)
		copy.db_insert()
		sle.db_set({"qty_after_transaction": 4, "stock_value": 400}, update_modified=False)

		return item

	def make_standard_cost_item(self, **properties) -> str:
		from erpnext.stock.doctype.item_standard_cost.test_item_standard_cost import (
			create_item_standard_cost,
			create_standard_cost_item,
		)

		item = create_standard_cost_item(**properties).name
		create_item_standard_cost(item, rate=100, company=COMPANY, effective_date=last_year(70))
		return item

	def make_standard_cost_balance_qty_wrong(self) -> str:
		"""A Standard Cost item at 100: the issue left a balance of 7 at 700 behind, where 6 are on
		hand."""
		item = self.make_standard_cost_item()

		make_stock_entry(item_code=item, target=WAREHOUSE, qty=10, basic_rate=100, posting_date=last_year(60))
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=4, posting_date=last_year(50))
		self.corrupt_entry(
			issue.name,
			qty_after_transaction=7,
			stock_value=700,
			stock_value_difference=-300,
			stock_queue=frappe.as_json([[7, 100]]),
		)
		make_stock_entry(item_code=item, source=WAREHOUSE, qty=1, posting_date=this_year(1))

		return item

	def make_standard_cost_serial_no_issued_at_wrong_value(self) -> str:
		"""A serialized Standard Cost item at 100: 3 received, one issued at 150."""
		item = self.make_standard_cost_item(has_serial_no=1, serial_no_series="SVA-SCS-.#####")

		receipt = make_stock_entry(
			item_code=item, target=WAREHOUSE, qty=3, basic_rate=100, posting_date=last_year(60)
		)
		serial_no = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, "serial_no"
		)
		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=1, serial_no=[serial_no], posting_date=last_year(50)
		)
		self.corrupt_entry(issue.name, stock_value_difference=-150, stock_value=150)

		return item


class TestFixingWrongLedgers(ValuationFixTestCase):
	def test_fifo_issue_at_wrong_value_fixed_by_repost(self):
		self.fix_by_repost(self.make_fifo_issue_at_wrong_value())

	def test_fifo_issue_at_wrong_value_fixed_by_adjustment_entry(self):
		item = self.make_fifo_issue_at_wrong_value()
		adjustment = self.fix_by_adjustment_entry(item)

		# the FIFO queue is counted back in layer by layer: 6 at 100, then 10 at 150
		self.assertEqual([(row.qty, row.valuation_rate) for row in adjustment.items], [(6, 100), (10, 150)])
		self.assertEqual(adjustment.difference_amount, 50)

		# so what goes out after it still leaves from the oldest layer
		issue = make_stock_entry(item_code=item, source=WAREHOUSE, qty=5, posting_date=nowdate())
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry", {"voucher_no": issue.name, "is_cancelled": 0}, "stock_value_difference"
			),
			-(4 * 100 + 1 * 150),
		)
		self.assertEqual(self.run_report(item), [])

	def test_moving_average_value_drift_fixed_by_repost(self):
		self.fix_by_repost(self.make_moving_average_value_drift())

	def test_moving_average_value_drift_fixed_by_adjustment_entry(self):
		adjustment = self.fix_by_adjustment_entry(self.make_moving_average_value_drift())

		self.assertEqual([(row.qty, row.valuation_rate) for row in adjustment.items], [(6, 100)])
		self.assertEqual(adjustment.difference_amount, 30)

	def test_wrong_balance_qty_fixed_by_repost(self):
		item = self.make_wrong_balance_qty()
		self.fix_by_repost(item)
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": WAREHOUSE}, "actual_qty"), 6
		)

	def test_wrong_balance_qty_fixed_by_adjustment_entry(self):
		item = self.make_wrong_balance_qty()
		self.fix_by_adjustment_entry(item)
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": WAREHOUSE}, "actual_qty"), 6
		)

	def test_batch_issued_at_wrong_value_fixed_by_repost(self):
		self.fix_by_repost(self.make_batch_issued_at_wrong_value())

	def test_batch_issued_at_wrong_value_fixed_by_adjustment_entry(self):
		item = self.make_batch_issued_at_wrong_value()
		adjustment = self.fix_by_adjustment_entry(item)

		self.assertEqual([(row.qty, row.valuation_rate) for row in adjustment.items], [(6, 100)])
		batch_no = adjustment.items[0].batch_no
		self.assertEqual(frappe.db.get_value("Batch", batch_no, "batch_qty"), 5)

	def test_batch_holding_value_with_no_qty_fixed_by_repost(self):
		item, _empty_batch = self.make_batch_holding_value_with_no_qty()
		self.fix_by_repost(item)

	def test_batch_holding_value_with_no_qty_fixed_by_adjustment_entry(self):
		item, empty_batch = self.make_batch_holding_value_with_no_qty()
		self.fix_by_adjustment_entry(item)

		# the batch no longer carries the 200: new stock of it goes out at its own rate
		make_stock_entry(
			item_code=item,
			target=WAREHOUSE,
			qty=10,
			rate=300,
			batch_no=empty_batch,
			posting_date=nowdate(),
		)
		issue = make_stock_entry(
			item_code=item, source=WAREHOUSE, qty=5, batch_no=empty_batch, posting_date=nowdate()
		)
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry", {"voucher_no": issue.name, "is_cancelled": 0}, "stock_value_difference"
			),
			-5 * 300,
		)
		self.assertEqual(frappe.db.get_value("Batch", empty_batch, "batch_qty"), 5)
		self.assertEqual(self.run_report(item), [])

	def test_pooled_batches_from_wrong_layer_fixed_by_repost(self):
		self.fix_by_repost(self.make_pooled_batches_from_wrong_layer())

	def test_pooled_batches_from_wrong_layer_fixed_by_adjustment_entry(self):
		adjustment = self.fix_by_adjustment_entry(self.make_pooled_batches_from_wrong_layer())

		# the batches are spread over the pool's layers: 6 at 100, then 10 at 150
		self.assertEqual(
			sorted((row.qty, row.valuation_rate) for row in adjustment.items), [(4, 150), (6, 100), (6, 150)]
		)

	def test_pool_value_no_batch_holds_fixed_by_repost(self):
		self.fix_by_repost(self.make_pool_value_no_batch_holds())

	def test_pool_value_no_batch_holds_fixed_by_adjustment_entry(self):
		adjustment = self.fix_by_adjustment_entry(self.make_pool_value_no_batch_holds())
		self.assertEqual(adjustment.difference_amount, 100)

	def test_serial_no_issued_at_wrong_value_fixed_by_repost(self):
		self.fix_by_repost(self.make_serial_no_issued_at_wrong_value())

	def test_serial_no_issued_at_wrong_value_fixed_by_adjustment_entry(self):
		item = self.make_serial_no_issued_at_wrong_value()
		adjustment = self.fix_by_adjustment_entry(item)

		# every serial no is counted back in at the rate of its receipt
		self.assertEqual(
			sorted((row.qty, row.valuation_rate) for row in adjustment.items), [(1, 100), (2, 200)]
		)
		self.assertEqual(adjustment.difference_amount, 50)

	def test_serial_no_counted_twice_fixed_by_adjustment_entry(self):
		# a repost cannot take out an entry that should not be there; an adjustment can
		item = self.make_serial_no_counted_twice()
		adjustment = self.fix_by_adjustment_entry(item)

		self.assertEqual([(row.qty, row.valuation_rate) for row in adjustment.items], [(2, 100)])
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": WAREHOUSE}, "actual_qty"), 2
		)

	def test_standard_cost_balance_qty_wrong_fixed_by_repost(self):
		self.fix_by_repost(self.make_standard_cost_balance_qty_wrong())

	def test_standard_cost_balance_qty_wrong_fixed_by_adjustment_entry(self):
		item = self.make_standard_cost_balance_qty_wrong()
		adjustment = self.fix_by_adjustment_entry(item)

		# the stock is counted back in at the standard rate on the date
		self.assertEqual([(row.qty, row.valuation_rate) for row in adjustment.items], [(6, 100)])
		self.assertEqual(
			frappe.db.get_value("Bin", {"item_code": item, "warehouse": WAREHOUSE}, "actual_qty"), 5
		)

	def test_standard_cost_serial_no_issued_at_wrong_value_fixed_by_repost(self):
		self.fix_by_repost(self.make_standard_cost_serial_no_issued_at_wrong_value())

	def test_standard_cost_serial_no_issued_at_wrong_value_fixed_by_adjustment_entry(self):
		item = self.make_standard_cost_serial_no_issued_at_wrong_value()
		adjustment = self.fix_by_adjustment_entry(item)

		# the serial nos on hand come back in at the standard rate
		self.assertEqual([(row.qty, row.valuation_rate) for row in adjustment.items], [(2, 100)])
		self.assertEqual(len(get_serial_nos(adjustment.items[0].serial_no)), 2)
		self.assertEqual(adjustment.difference_amount, 50)


class TestAdjustmentEntry(ValuationFixTestCase):
	def test_difference_is_booked_to_the_difference_account(self):
		warehouse = "Stores - TCP1"
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		item = make_item(properties={"is_stock_item": 1, "valuation_method": "FIFO"}).name
		make_stock_entry(item_code=item, target=warehouse, qty=10, rate=100, posting_date=last_year(60))
		issue = make_stock_entry(item_code=item, source=warehouse, qty=4, posting_date=last_year(50))
		self.corrupt_entry(issue.name, stock_value_difference=-450, stock_value=550)

		differences = [
			row.stock_ledger_entry
			for row in execute(frappe._dict(company=company, item_code=item, show=SHOW_ALL_DIFFERENCES))[1]
		]
		result = make_adjustment_entry(company, differences, get_adjustment_date(), "00:00:00")
		adjustment = frappe.get_doc("Stock Reconciliation", result["adjustment_entry"])
		adjustment.submit()

		gl_entries = {
			gle.account: flt(gle.debit) - flt(gle.credit)
			for gle in frappe.get_all(
				"GL Entry",
				filters={"voucher_no": adjustment.name, "is_cancelled": 0},
				fields=["account", "debit", "credit"],
			)
		}
		inventory_account = frappe.db.get_value("Warehouse", warehouse, "account") or frappe.get_cached_value(
			"Company", company, "default_inventory_account"
		)
		self.assertEqual(gl_entries, {inventory_account: 50, adjustment.expense_account: -50})

		# and nothing is booked in the past fiscal year
		self.assertFalse(
			frappe.db.exists(
				"GL Entry",
				{"voucher_no": adjustment.name, "posting_date": ("<", get_adjustment_date())},
			)
		)

	def test_stock_balance_shows_the_net_change(self):
		item = self.make_fifo_issue_at_wrong_value()
		before = self.get_balance_movement(item)
		self.fix_by_adjustment_entry(item)
		after = self.get_balance_movement(item)

		# the reset counts 16 out and back in, which Stock Balance shows as the 50 it adds
		self.assertEqual((after.in_qty, after.out_qty), (before.in_qty, before.out_qty))
		self.assertEqual(flt(after.in_val) - flt(before.in_val), 50)
		self.assertEqual(after.bal_qty, before.bal_qty)

	def test_stock_ageing_keeps_the_age_of_what_is_counted_back_in(self):
		item = self.make_serial_no_issued_at_wrong_value()
		before = self.get_fifo_queue(item)
		self.fix_by_adjustment_entry(item)

		self.assertEqual(self.get_fifo_queue(item), before)
		self.assertTrue(all(str(slot[1]) < get_adjustment_date() for slot in before))

	def test_stock_ageing_keeps_the_age_of_batches(self):
		item = self.make_batch_issued_at_wrong_value()
		ages = [slot[3] for slot in self.get_fifo_queue(item)]
		self.fix_by_adjustment_entry(item)

		self.assertEqual([slot[3] for slot in self.get_fifo_queue(item)], ages)

	def test_invariant_check_reads_the_reset_as_stock_moving(self):
		from erpnext.stock.report.stock_ledger_invariant_check.stock_ledger_invariant_check import get_data

		item = self.make_fifo_issue_at_wrong_value()
		adjustment = self.fix_by_adjustment_entry(item)

		entries = get_data(frappe._dict(item_code=item, warehouse=WAREHOUSE))
		reset = [entry for entry in entries if entry.voucher_no == adjustment.name]
		self.assertTrue(len(reset) > 1)
		self.assertTrue(all(not flt(entry.difference_in_qty) for entry in reset))

	def test_consumption_leaves_the_reset_out(self):
		from erpnext.stock.report.item_wise_consumption.item_wise_consumption import get_consumed_details

		item = self.make_fifo_issue_at_wrong_value()
		adjustment = self.fix_by_adjustment_entry(item)

		consumed = get_consumed_details(frappe._dict(from_date=get_adjustment_date(), to_date=nowdate()))
		self.assertNotIn(adjustment.name, {entry.voucher_no for entry in consumed.get(item, [])})

	def test_cancelling_the_adjustment_entry_restores_the_ledger(self):
		item = self.make_batch_issued_at_wrong_value()
		differences = self.get_differences(item)
		batch_no = frappe.db.get_value("Batch", {"item": item}, "name")
		adjustment = self.fix_by_adjustment_entry(item)

		adjustment.reload()
		adjustment.cancel()

		self.assertEqual(self.get_differences(item), differences)
		self.assertEqual(frappe.db.get_value("Batch", batch_no, "batch_qty"), 5)
		self.assertFalse(
			frappe.db.exists("Stock Ledger Entry", {"voucher_no": adjustment.name, "is_cancelled": 0})
		)

	def test_difference_after_the_adjustment_date_is_not_settled_by_it(self):
		item = self.make_fifo_issue_at_wrong_value()

		result = make_adjustment_entry(COMPANY, self.get_differences(item), last_year(52), "00:00:00")
		self.assertIsNone(result["adjustment_entry"])
		self.assertEqual(len(result["not_adjusted"]), 1)

	def test_rows_must_be_the_stock_it_should_hold(self):
		item = self.make_fifo_issue_at_wrong_value()
		result = make_adjustment_entry(COMPANY, self.get_differences(item), get_adjustment_date(), "00:00:00")

		adjustment = frappe.get_doc("Stock Reconciliation", result["adjustment_entry"])
		adjustment.items[0].valuation_rate = 90
		self.assertRaises(frappe.ValidationError, adjustment.save)

	def test_no_backdated_entry_before_an_adjustment_entry(self):
		item = self.make_fifo_issue_at_wrong_value()
		issue = frappe.get_last_doc("Stock Entry", filters={"posting_date": last_year(50)})
		adjustment = self.fix_by_adjustment_entry(item)

		self.assertRaises(
			BackdatedEntryBeforeAdjustmentError,
			make_stock_entry,
			item_code=item,
			target=WAREHOUSE,
			qty=1,
			rate=100,
			posting_date=last_year(10),
		)
		issue.reload()
		self.assertRaises(BackdatedEntryBeforeAdjustmentError, issue.cancel)

		# on or after the adjustment is fine
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=1, rate=100, posting_date=nowdate())

		# and once the adjustment is cancelled, so is before it
		adjustment.reload()
		adjustment.cancel()
		make_stock_entry(item_code=item, target=WAREHOUSE, qty=1, rate=100, posting_date=last_year(10))

	def test_no_backdated_entry_of_an_adjusted_batch(self):
		item = self.make_batch_issued_at_wrong_value()
		batch_no = frappe.db.get_value("Batch", {"item": item}, "name")
		self.fix_by_adjustment_entry(item)

		# the batch cannot move before the adjustment, even into another warehouse
		self.assertRaises(
			BackdatedEntryBeforeAdjustmentError,
			make_stock_entry,
			item_code=item,
			source=WAREHOUSE,
			target="_Test Warehouse 1 - _TC",
			qty=1,
			batch_no=batch_no,
			posting_date=last_year(10),
		)

	def test_reserved_stock_blocks_an_adjustment_that_changes_qty(self):
		item = self.make_wrong_balance_qty()
		result = make_adjustment_entry(COMPANY, self.get_differences(item), get_adjustment_date(), "00:00:00")
		adjustment = frappe.get_doc("Stock Reconciliation", result["adjustment_entry"])

		# the ledger holds 7 and the adjustment sets 6, which reserved stock may not allow
		with patch_reserved_qty({(item, WAREHOUSE): 1}):
			self.assertRaises(frappe.ValidationError, adjustment.submit)

	def test_reserved_stock_does_not_block_an_adjustment_of_value_alone(self):
		item = self.make_fifo_issue_at_wrong_value()
		result = make_adjustment_entry(COMPANY, self.get_differences(item), get_adjustment_date(), "00:00:00")
		adjustment = frappe.get_doc("Stock Reconciliation", result["adjustment_entry"])

		with patch_reserved_qty({(item, WAREHOUSE): 1}) as reserved_qty:
			adjustment.submit()

		reserved_qty.assert_called_once_with([], [])


class TestPermissions(ValuationFixTestCase):
	def test_company_user_permission(self):
		item = self.make_fifo_issue_at_wrong_value()
		differences = self.get_differences(item)

		frappe.set_user(make_stock_manager("svc-restricted@example.com", company="_Test Company 1"))
		try:
			self.assertRaises(frappe.PermissionError, self.run_report, item)
			self.assertRaises(frappe.PermissionError, get_repost_preview, COMPANY, differences)
			self.assertRaises(
				frappe.PermissionError,
				make_adjustment_entry,
				COMPANY,
				differences,
				get_adjustment_date(),
				"00:00:00",
			)
		finally:
			frappe.set_user("Administrator")


def patch_reserved_qty(reserved_qty: dict):
	"""Stock reserved for the item-warehouses, as reservations would leave it."""

	def get_reserved_qty(item_codes, warehouses):
		return {
			key: qty for key, qty in reserved_qty.items() if key[0] in item_codes and key[1] in warehouses
		}

	return patch(
		"erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry.get_sre_reserved_qty_for_items_and_warehouses",
		side_effect=get_reserved_qty,
	)


class TestRepost(ValuationFixTestCase):
	def test_repost_starts_at_the_first_difference(self):
		item = self.make_fifo_issue_at_wrong_value()
		wrong_sle = self.get_differences(item)[0]

		preview = get_repost_preview(COMPANY, [wrong_sle])
		self.assertEqual(len(preview), 1)
		self.assertEqual(str(preview[0]["posting_date"]), last_year(50))
		self.assertIsNone(preview[0]["pending_repost"])

	def test_repost_warns_of_a_past_fiscal_year(self):
		item = self.make_fifo_issue_at_wrong_value()

		preview = get_repost_preview(COMPANY, self.get_differences(item))
		self.assertTrue(preview[0]["is_past_fiscal_year"])
		self.assertEqual(preview[0]["fiscal_year"], get_fiscal_year(last_year(50), company=COMPANY)[0])

	def test_pending_repost_is_shown_and_not_made_twice(self):
		item = self.make_fifo_issue_at_wrong_value()
		differences = self.get_differences(item)

		frappe.flags.dont_execute_stock_reposts = True
		try:
			result = make_repost_entries(COMPANY, differences)
			repost = frappe.get_doc("Repost Item Valuation", result["created"][0]["repost"])
			self.assertEqual((repost.item_code, repost.warehouse, repost.status), (item, WAREHOUSE, "Queued"))

			self.assertEqual(self.run_report(item)[0].pending_repost, repost.name)
			result = make_repost_entries(COMPANY, differences)
			self.assertEqual(result["created"], [])
			self.assertEqual(len(result["not_created"]), 1)
		finally:
			frappe.flags.dont_execute_stock_reposts = False

		run_repost(repost)
		self.assertEqual(self.run_report(item, show_adjusted_differences=1), [])
