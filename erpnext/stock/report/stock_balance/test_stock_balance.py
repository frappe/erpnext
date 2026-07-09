from typing import Any

import frappe
from frappe import _dict
from frappe.utils import today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_balance.stock_balance import execute, get_stock_ageing_data
from erpnext.tests.utils import ERPNextTestSuite


def stock_balance(filters):
	"""Get rows from stock balance report"""
	return [_dict(row) for row in execute(filters)[1]]


class TestStockBalance(ERPNextTestSuite):
	# ----------- utils

	# `_Test Item` is a committed bootstrap item that starts at zero stock in `Stores - _TC`,
	# so transacting here keeps exact qty/value assertions deterministic.
	test_warehouse = "Stores - _TC"

	def setUp(self):
		self.item = frappe.get_doc("Item", "_Test Item")
		self.filters = _dict(
			{
				"company": "_Test Company",
				"item_code": [self.item.name],
				"warehouse": self.test_warehouse,
				"from_date": "2020-01-01",
				"to_date": str(today()),
			}
		)

	def assertPartialDictEq(self, expected: dict[str, Any], actual: dict[str, Any]):
		for k, v in expected.items():
			self.assertEqual(v, actual[k], msg=f"{expected=}\n{actual=}")

	def generate_stock_ledger(self, item_code: str, movements):
		for movement in map(_dict, movements):
			if "to_warehouse" not in movement:
				movement.to_warehouse = self.test_warehouse
			make_stock_entry(item_code=item_code, **movement)

	def assertInvariants(self, rows):
		item_wh_stock = _dict()

		# Latest balance per (item_code, warehouse): first row wins because of the desc ordering.
		for line in frappe.get_all(
			"Stock Ledger Entry",
			filters={"is_cancelled": 0},
			fields=["item_code", "warehouse", "stock_value", "qty_after_transaction"],
			order_by="posting_datetime desc, creation desc",
		):
			item_wh_stock.setdefault((line.item_code, line.warehouse), line)

		for row in rows:
			msg = f"Invariants not met for {rows=}"
			# qty invariant
			self.assertAlmostEqual(row.bal_qty, row.opening_qty + row.in_qty - row.out_qty, msg)

			# value invariant
			self.assertAlmostEqual(row.bal_val, row.opening_val + row.in_val - row.out_val, msg)

			# check against SLE
			last_sle = item_wh_stock[(row.item_code, row.warehouse)]
			self.assertAlmostEqual(row.bal_qty, last_sle.qty_after_transaction, 3)
			self.assertAlmostEqual(row.bal_val, last_sle.stock_value, 3)

			# valuation rate
			if not row.bal_qty:
				continue
			self.assertAlmostEqual(row.val_rate, row.bal_val / row.bal_qty, 3, msg)

	# ----------- tests

	def test_basic_stock_balance(self):
		"""Check very basic functionality and item info"""
		rows = stock_balance(self.filters)
		self.assertEqual(rows, [])

		self.generate_stock_ledger(self.item.name, [_dict(qty=5, rate=10)])

		# check item info
		rows = stock_balance(self.filters)
		self.assertPartialDictEq(
			{
				"item_code": self.item.name,
				"item_name": self.item.item_name,
				"item_group": self.item.item_group,
				"stock_uom": self.item.stock_uom,
				"in_qty": 5,
				"in_val": 50,
				"val_rate": 10,
			},
			rows[0],
		)
		self.assertInvariants(rows)

	def test_include_zero_stock_items(self):
		"""Items whose balance nets to zero are hidden by default and shown only when the filter is on."""
		self.generate_stock_ledger(
			self.item.name,
			[
				_dict(qty=5, rate=10),
				_dict(qty=5, from_warehouse=self.test_warehouse, to_warehouse=None),
			],
		)

		self.assertEqual(stock_balance(self.filters), [])

		rows = stock_balance(self.filters.update({"include_zero_stock_items": 1}))
		self.assertEqual(rows[0].item_code, self.item.name)
		self.assertEqual(rows[0].bal_qty, 0)
		self.assertEqual(rows[0].bal_val, 0)

	def test_show_stock_ageing_data_adds_ageing_columns(self):
		"""The ageing columns appear only when 'show stock ageing data' is on."""
		self.generate_stock_ledger(self.item.name, [_dict(qty=5, rate=10, posting_date="2021-01-01")])

		self.assertNotIn("average_age", stock_balance(self.filters)[0])

		rows = stock_balance(self.filters.update({"show_stock_ageing_data": 1}))
		self.assertIn("average_age", rows[0])
		self.assertGreater(rows[0].average_age, 0)  # stock has been held since 2021

	@ERPNextTestSuite.change_settings("System Settings", {"float_precision": 3, "currency_precision": 3})
	def test_opening_balance(self):
		self.generate_stock_ledger(
			self.item.name,
			[
				_dict(qty=1, rate=1, posting_date="2021-01-01"),
				_dict(qty=2, rate=2, posting_date="2021-01-02"),
				_dict(qty=3, rate=3, posting_date="2021-01-03"),
			],
		)
		rows = stock_balance(self.filters)
		self.assertInvariants(rows)

		rows = stock_balance(self.filters.update({"from_date": "2021-01-02"}))
		self.assertInvariants(rows)
		self.assertPartialDictEq({"opening_qty": 1, "in_qty": 5}, rows[0])

		rows = stock_balance(self.filters.update({"from_date": "2022-01-01"}))
		self.assertInvariants(rows)
		self.assertPartialDictEq({"opening_qty": 6, "in_qty": 0}, rows[0])

	def test_uom_converted_info(self):
		self.item.append("uoms", {"conversion_factor": 5, "uom": "Box"})
		self.item.save()

		self.generate_stock_ledger(self.item.name, [_dict(qty=5, rate=10)])

		rows = stock_balance(self.filters.update({"include_uom": "Box"}))
		self.assertEqual(rows[0].bal_qty_alt, 1)
		self.assertInvariants(rows)

	def test_item_group(self):
		self.generate_stock_ledger(self.item.name, [_dict(qty=5, rate=10)])

		self.filters.pop("item_code", None)
		rows = stock_balance(self.filters.update({"item_group": self.item.item_group}))
		self.assertTrue(rows)
		self.assertTrue(all(r.item_group == self.item.item_group for r in rows))

	def test_child_warehouse_balances(self):
		# This is default
		self.generate_stock_ledger(self.item.name, [_dict(qty=5, rate=10, to_warehouse="Stores - _TC")])

		self.filters.pop("item_code", None)
		rows = stock_balance(self.filters.update({"warehouse": "All Warehouses - _TC"}))

		self.assertTrue(
			any(r.item_code == self.item.name and r.warehouse == "Stores - _TC" for r in rows),
			msg=f"Expected child warehouse balances \n{rows}",
		)

	def test_show_item_attr(self):
		from erpnext.controllers.item_variant import create_variant

		attributes = {"Test Size": "Large"}
		variant = create_variant("_Test Variant Item", attributes)
		variant.save()

		self.generate_stock_ledger(variant.name, [_dict(qty=5, rate=10)])
		rows = stock_balance(self.filters.update({"show_variant_attributes": 1, "item_code": [variant.name]}))
		self.assertPartialDictEq(attributes, rows[0])
		self.assertInvariants(rows)

	def make_alt_uom_item(self, uoms=None):
		"""Fresh item with a controlled UOM table; `_Test Item` already carries an alternate
		UOM, which would shadow the "first alternate" assertions in these tests."""
		item = make_item(uoms=uoms)
		self.filters.update({"item_code": [item.name]})
		return item

	def test_alt_uom_balance_single_uom(self):
		"""Alt UOM columns show correct name and converted qty for an item with one alternate UOM."""
		item = self.make_alt_uom_item(uoms=[{"conversion_factor": 12, "uom": "Box"}])

		self.generate_stock_ledger(item.name, [_dict(qty=24, rate=10)])

		rows = stock_balance(self.filters.update({"show_alt_uom_balance": 1}))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].get("alt_uom"), "Box")
		self.assertAlmostEqual(rows[0].get("alt_uom_bal_qty"), 2.0)  # 24 / 12

	def test_alt_uom_balance_no_alternate_uom(self):
		"""Alt UOM columns are not added when no items in the report have alt UOMs."""
		item = self.make_alt_uom_item()
		self.generate_stock_ledger(item.name, [_dict(qty=5, rate=10)])

		columns, _ = execute(self.filters.update({"show_alt_uom_balance": 1}))
		col_fieldnames = [c.get("fieldname") for c in columns if isinstance(c, dict)]
		self.assertNotIn("alt_uom", col_fieldnames)
		self.assertNotIn("alt_uom_bal_qty", col_fieldnames)

	def test_alt_uom_balance_filter_disabled(self):
		"""No alt UOM columns are injected when show_alt_uom_balance is not set."""
		item = self.make_alt_uom_item(uoms=[{"conversion_factor": 12, "uom": "Box"}])

		self.generate_stock_ledger(item.name, [_dict(qty=24, rate=10)])

		columns, _ = execute(self.filters)
		col_fieldnames = [c.get("fieldname") for c in columns if isinstance(c, dict)]
		self.assertNotIn("alt_uom", col_fieldnames)
		self.assertNotIn("alt_uom_bal_qty", col_fieldnames)

	def test_alt_uom_balance_uses_first_alternate_uom(self):
		"""When an item has multiple alt UOMs, only the first (lowest idx) is shown."""
		frappe.get_doc({"doctype": "UOM", "uom_name": "Carton"}).insert(ignore_if_duplicate=True)
		item = self.make_alt_uom_item(
			uoms=[
				{"conversion_factor": 12, "uom": "Box"},
				{"conversion_factor": 144, "uom": "Carton"},
			]
		)

		self.generate_stock_ledger(item.name, [_dict(qty=144, rate=10)])

		rows = stock_balance(self.filters.update({"show_alt_uom_balance": 1}))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].get("alt_uom"), "Box")
		self.assertAlmostEqual(rows[0].get("alt_uom_bal_qty"), 12.0)  # 144 / 12, not 144 / 144

	def test_stock_ageing_data_accepts_batchwise_valuation_slots(self):
		fifo_queue = [
			["SA-BATCH-NEWER", 1, 2.0, "2021-12-05", 20.0],
			["SA-BATCH-OLDER", 1, 3.0, "2021-12-01", 30.0],
		]

		stock_ageing_data = get_stock_ageing_data(fifo_queue, "2021-12-10")

		self.assertEqual(stock_ageing_data["average_age"], 7.4)
		self.assertEqual(stock_ageing_data["earliest_age"], 9)
		self.assertEqual(stock_ageing_data["latest_age"], 5)
		self.assertEqual(
			stock_ageing_data["fifo_queue"],
			[[3.0, "2021-12-01", 30.0], [2.0, "2021-12-05", 20.0]],
		)
