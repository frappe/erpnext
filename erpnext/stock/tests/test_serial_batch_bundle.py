# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.serial_batch_bundle import (
	SerialBatchCreation,
	combine_datetime,
	get_available_batches_qty,
	get_qty_based_available_batches,
	get_serial_nos_based_on_posting_date,
	get_type_of_transaction,
	parse_serial_nos,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchBundleLogic(ERPNextTestSuite):
	"""Pure helpers and in-memory validation logic from erpnext.stock.serial_batch_bundle,
	which resolves and validates serial/batch composition before it is written to Stock
	Location Ledger."""

	def make_creation(self, **overrides):
		kwargs = {
			"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC",
			"type_of_transaction": "Inward",
			"voucher_type": "Stock Entry",
		}
		kwargs.update(overrides)
		return SerialBatchCreation(kwargs)

	def test_parse_serial_nos_splits_and_trims(self):
		self.assertEqual(parse_serial_nos("SN1\nSN2"), ["SN1", "SN2"])
		self.assertEqual(parse_serial_nos("SN1, SN2 , SN3"), ["SN1", "SN2", "SN3"])
		# blanks are dropped and an existing list is returned unchanged
		self.assertEqual(parse_serial_nos("SN1,,\n , SN2"), ["SN1", "SN2"])
		self.assertEqual(parse_serial_nos(["SN1", "SN2"]), ["SN1", "SN2"])

	def test_get_qty_based_available_batches_allocates_across_batches(self):
		batches = [
			frappe._dict(batch_no="B1", qty=10, warehouse="W"),
			frappe._dict(batch_no="B2", qty=5, warehouse="W"),
		]
		# 12 consumes B1 fully then 2 from B2
		result = get_qty_based_available_batches(batches, 12)
		self.assertEqual([(b.batch_no, b.qty) for b in result], [("B1", 10), ("B2", 2)])
		# 8 is satisfied by B1 alone; B2 is not touched
		result = get_qty_based_available_batches(batches, 8)
		self.assertEqual([(b.batch_no, b.qty) for b in result], [("B1", 8)])

	def test_get_available_batches_qty_aggregates_by_batch(self):
		batches = [
			frappe._dict(batch_no="B1", qty=10),
			frappe._dict(batch_no="B2", qty=5),
			frappe._dict(batch_no="B1", qty=3),
		]
		agg = get_available_batches_qty(batches)
		self.assertEqual(agg["B1"], 13)
		self.assertEqual(agg["B2"], 5)

	def test_get_type_of_transaction_derives_direction(self):
		def se(**kw):
			return get_type_of_transaction(frappe._dict(doctype="Stock Entry"), frappe._dict(**kw))

		self.assertEqual(se(s_warehouse="W"), "Outward")  # issuing from a source warehouse
		self.assertEqual(se(), "Inward")  # only a target warehouse
		self.assertEqual(
			get_type_of_transaction(frappe._dict(doctype="Purchase Receipt"), frappe._dict()), "Inward"
		)
		self.assertEqual(
			get_type_of_transaction(frappe._dict(doctype="Stock Reconciliation"), frappe._dict()), "Inward"
		)
		# a purchase return reverses the direction to Outward
		self.assertEqual(
			get_type_of_transaction(frappe._dict(doctype="Purchase Receipt", is_return=1), frappe._dict()),
			"Outward",
		)

	def test_duplicate_serial_no_in_entries_is_rejected(self):
		creation = self.make_creation()
		entries = [frappe._dict(idx=1, serial_no="SN1"), frappe._dict(idx=2, serial_no="SN1")]
		self.assertRaises(frappe.ValidationError, creation.validate_duplicate_serial_and_batch_no, entries)

	def test_duplicate_batch_no_in_entries_is_rejected(self):
		creation = self.make_creation()
		entries = [frappe._dict(idx=1, batch_no="B1"), frappe._dict(idx=2, batch_no="B1")]
		self.assertRaises(frappe.ValidationError, creation.validate_duplicate_serial_and_batch_no, entries)

	def test_calculate_total_qty_normalizes_and_signs(self):
		inward = self.make_creation(type_of_transaction="Inward")
		self.assertEqual(inward.calculate_total_qty([frappe._dict(qty=5), frappe._dict(qty=3)]), 8)

		# Outward flips the sign
		outward = self.make_creation(type_of_transaction="Outward")
		self.assertEqual(outward.calculate_total_qty([frappe._dict(qty=5)]), -5)

		# a serialized bundle normalizes each row qty to 1
		serialized = self.make_creation(type_of_transaction="Inward")
		serialized.has_serial_no = 1
		self.assertEqual(serialized.calculate_total_qty([frappe._dict(qty=5)]), 1)

	def test_get_serial_nos_based_on_posting_date(self):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			get_serial_nos_for_voucher,
		)

		item_code = make_item(properties={"has_serial_no": 1, "serial_no_series": "TEST-BWSN-.#####"}).name
		warehouse = "_Test Warehouse - _TC"

		se_in = make_stock_entry(item_code=item_code, target=warehouse, qty=3, rate=100)
		serial_nos = get_serial_nos_for_voucher(se_in.doctype, se_in.name, warehouse=warehouse)

		kwargs = frappe._dict(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_datetime": combine_datetime(se_in.posting_date, se_in.posting_time),
			}
		)
		available = get_serial_nos_based_on_posting_date(kwargs, [])
		self.assertEqual(sorted(available), sorted(serial_nos))

		# consuming one serial no removes it from the availability computed as of a later point in time
		se_out = make_stock_entry(
			item_code=item_code,
			source=warehouse,
			qty=1,
			serial_no=serial_nos[0],
			use_serial_batch_fields=1,
		)
		kwargs.posting_datetime = combine_datetime(se_out.posting_date, se_out.posting_time)
		available = get_serial_nos_based_on_posting_date(kwargs, [])
		self.assertNotIn(serial_nos[0], available)
		self.assertEqual(sorted(available), sorted(serial_nos[1:]))
