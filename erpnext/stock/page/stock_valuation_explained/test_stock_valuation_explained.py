import frappe
from frappe.utils import add_days, today

from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.controllers.stock_controller import create_repost_item_valuation_entry
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.page.stock_valuation_explained.stock_valuation_explained import get_valuation_steps
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"


class TestStockValuationExplained(ERPNextTestSuite):
	def make_item(self, valuation_method, **properties):
		properties.update({"is_stock_item": 1, "valuation_method": valuation_method})
		return make_item(properties=properties).name

	def receive(self, item_code, rate, days_ago):
		return make_purchase_receipt(
			item_code=item_code,
			qty=1,
			rate=rate,
			warehouse=WAREHOUSE,
			posting_date=add_days(today(), -days_ago),
		)

	def get_entry_name(self, voucher_no):
		return frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": voucher_no, "is_cancelled": 0}, "name"
		)

	def make_purchase_return(self, item_code):
		first = self.receive(item_code, 50, 2)
		self.receive(item_code, 60, 1)
		purchase_return = make_return_doc("Purchase Receipt", first.name)
		purchase_return.submit()
		return first, self.get_entry_name(purchase_return.name)

	def test_purchase_return_shows_the_rate_used_and_the_original_rate(self):
		item_code = self.make_item("Moving Average")
		first, entry = self.make_purchase_return(item_code)

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=entry)

		self.assertEqual(len(steps.entries), 3)
		self.assertEqual(steps.entries[0].qty_before, 0)
		self.assertEqual(steps.entries[1].rate_after, 55)
		returned = steps.entries[-1]
		self.assertEqual(returned.kind, "out")
		self.assertEqual(returned.return_against, first.name)
		self.assertEqual((returned.rate, returned.original_rate), (50, 50))
		self.assertEqual((returned.qty_after, returned.value_after, returned.rate_after), (1, 60, 60))

	def test_moving_average_purchase_return_after_repost_goes_out_at_average(self):
		item_code = self.make_item("Moving Average")
		_first, entry = self.make_purchase_return(item_code)
		create_repost_item_valuation_entry(
			{
				"based_on": "Item and Warehouse",
				"item_code": item_code,
				"warehouse": WAREHOUSE,
				"posting_date": add_days(today(), -2),
				"posting_time": "00:00:00",
				"company": "_Test Company",
			}
		)

		returned = get_valuation_steps(item_code, WAREHOUSE, upto=entry).entries[-1]

		self.assertEqual((returned.rate, returned.original_rate), (55, 50))
		self.assertEqual((returned.qty_after, returned.value_after, returned.rate_after), (1, 55, 55))

	def test_fifo_issue_lists_the_lot_used(self):
		item_code = self.make_item("FIFO")
		self.receive(item_code, 50, 2)
		self.receive(item_code, 60, 1)
		issue = make_stock_entry(item_code=item_code, source=WAREHOUSE, qty=1)

		steps = get_valuation_steps(item_code, WAREHOUSE, upto=self.get_entry_name(issue.name))
		issued = steps.entries[-1]

		self.assertEqual(issued.rate, 50)
		self.assertEqual(issued.used_lots, [[1, 50]])
		self.assertEqual(issued.lots_after, [[1, 60]])
		self.assertEqual(steps.entries[1].added_lots, [[1, 60]])

	def test_window_starts_where_stock_was_last_zero(self):
		item_code = self.make_item("Moving Average")
		self.receive(item_code, 50, 3)
		make_stock_entry(item_code=item_code, source=WAREHOUSE, qty=1, posting_date=add_days(today(), -2))
		last = self.receive(item_code, 70, 1)

		steps = get_valuation_steps(item_code, WAREHOUSE)

		self.assertEqual([entry.voucher_no for entry in steps.entries], [last.name])
		self.assertTrue(steps.has_earlier)
		self.assertEqual(steps.opening.qty, 0)

		earlier = get_valuation_steps(item_code, WAREHOUSE, before=steps.entries[0].name)
		self.assertEqual(len(earlier.entries), 2)
		self.assertFalse(earlier.has_earlier)

	def test_batch_item_is_not_explained_yet(self):
		item_code = self.make_item(
			"FIFO", has_batch_no=1, create_new_batch=1, batch_number_series="SVE-BATCH-.###"
		)

		steps = get_valuation_steps(item_code, WAREHOUSE)

		self.assertEqual(steps.item.unsupported, "batch")
		self.assertEqual(steps.entries, [])

	def test_entry_of_another_item_is_rejected(self):
		item_code = self.make_item("Moving Average")
		other = self.receive(self.make_item("Moving Average"), 50, 1)

		with self.assertRaises(frappe.ValidationError):
			get_valuation_steps(item_code, WAREHOUSE, upto=self.get_entry_name(other.name))
