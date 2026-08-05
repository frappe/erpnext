# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, flt, get_datetime, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
	cancel_stock_location_ledgers,
	repost_location_balance,
	submit_stock_location_ledgers,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestStockLocationLedger(ERPNextTestSuite):
	def make_draft_ledger(
		self,
		voucher_no,
		qty=1,
		batch_no=None,
		posting_datetime=None,
		submit=False,
		rack=None,
		bin=None,
		stock_value_difference=0,
	):
		doc = frappe.get_doc(
			{
				"doctype": "Stock Location Ledger",
				"item_code": self.item,
				"warehouse": "_Test Warehouse - _TC",
				"company": "_Test Company",
				"qty": qty,
				"batch_no": batch_no,
				"rack": rack,
				"bin": bin,
				"stock_value_difference": stock_value_difference,
				"is_outward": 1 if qty < 0 else 0,
				"voucher_type": "Stock Entry",
				"voucher_no": voucher_no,
				"voucher_detail_no": frappe.generate_hash(length=10),
				"posting_datetime": posting_datetime or frappe.utils.now(),
			}
		)
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		if submit:
			frappe.db.set_value("Stock Location Ledger", doc.name, "docstatus", 1)
		return doc

	def setUp(self):
		self.item = make_item(properties={"is_stock_item": 1}).name

	def test_qb_submit_and_cancel_transitions(self):
		voucher_no = frappe.generate_hash(length=10)
		rows = [self.make_draft_ledger(voucher_no) for _ in range(3)]

		for row in rows:
			self.assertEqual(frappe.db.get_value("Stock Location Ledger", row.name, "docstatus"), 0)

		submit_stock_location_ledgers("Stock Entry", voucher_no)
		for row in rows:
			self.assertEqual(frappe.db.get_value("Stock Location Ledger", row.name, "docstatus"), 1)

		cancel_stock_location_ledgers("Stock Entry", voucher_no)
		for row in rows:
			self.assertEqual(frappe.db.get_value("Stock Location Ledger", row.name, "docstatus"), 2)

	def test_transition_scoped_to_voucher(self):
		voucher_a = frappe.generate_hash(length=10)
		voucher_b = frappe.generate_hash(length=10)
		row_a = self.make_draft_ledger(voucher_a)
		row_b = self.make_draft_ledger(voucher_b)

		submit_stock_location_ledgers("Stock Entry", voucher_a)

		self.assertEqual(frappe.db.get_value("Stock Location Ledger", row_a.name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Stock Location Ledger", row_b.name, "docstatus"), 0)

	def test_promotion_restamps_voucher_posting_datetime(self):
		voucher_no = frappe.generate_hash(length=10)
		row = self.make_draft_ledger(voucher_no, posting_datetime=frappe.utils.now())
		voucher_posting_datetime = get_datetime("2026-01-01 10:00:00")

		submit_stock_location_ledgers("Stock Entry", voucher_no, posting_datetime=voucher_posting_datetime)

		self.assertEqual(
			get_datetime(frappe.db.get_value("Stock Location Ledger", row.name, "posting_datetime")),
			voucher_posting_datetime,
		)

	def qty_after(self, name):
		return frappe.db.get_value("Stock Location Ledger", name, "qty_after_transaction")

	def test_running_balance_maintained_in_posting_order(self):
		batch = frappe.generate_hash(length=10)
		r1 = self.make_draft_ledger(frappe.generate_hash(length=10), qty=10, batch_no=batch, submit=True)
		r2 = self.make_draft_ledger(frappe.generate_hash(length=10), qty=-4, batch_no=batch, submit=True)
		r3 = self.make_draft_ledger(frappe.generate_hash(length=10), qty=6, batch_no=batch, submit=True)

		repost_location_balance(
			{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
		)

		self.assertEqual(self.qty_after(r1.name), 10)
		self.assertEqual(self.qty_after(r2.name), 6)
		self.assertEqual(self.qty_after(r3.name), 12)

	def test_draft_rows_excluded_from_balance_until_submitted(self):
		batch = frappe.generate_hash(length=10)
		submitted = self.make_draft_ledger(
			frappe.generate_hash(length=10), qty=10, batch_no=batch, submit=True
		)
		draft = self.make_draft_ledger(frappe.generate_hash(length=10), qty=-4, batch_no=batch)

		repost_location_balance(
			{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
		)

		self.assertEqual(self.qty_after(submitted.name), 10)
		self.assertEqual(self.qty_after(draft.name), 0)

		frappe.db.set_value("Stock Location Ledger", draft.name, "docstatus", 1)
		repost_location_balance(
			{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
		)
		self.assertEqual(self.qty_after(draft.name), 6)

	def test_draft_ledgers_reconciled_with_valuation_on_posting(self):
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			make_stock_location_ledgers_from_sle,
		)

		batch = frappe.generate_hash(length=10)
		voucher_no = frappe.generate_hash(length=10)
		detail_no = frappe.generate_hash(length=10)

		draft = self.make_draft_ledger(voucher_no, qty=8, batch_no=batch)
		frappe.db.set_value("Stock Location Ledger", draft.name, "voucher_detail_no", detail_no)
		self.assertEqual(frappe.db.get_value("Stock Location Ledger", draft.name, "incoming_rate"), 0)

		sle = frappe._dict(
			{
				"item_code": self.item,
				"warehouse": "_Test Warehouse - _TC",
				"company": "_Test Company",
				"batch_no": batch,
				"actual_qty": 8,
				"incoming_rate": 100,
				"voucher_type": "Stock Entry",
				"voucher_no": voucher_no,
				"voucher_detail_no": detail_no,
				"posting_datetime": frappe.utils.now(),
				"is_cancelled": 0,
			}
		)
		make_stock_location_ledgers_from_sle(sle)

		row = frappe.db.get_value(
			"Stock Location Ledger",
			{"voucher_no": voucher_no, "batch_no": batch},
			["name", "docstatus", "incoming_rate", "qty_after_transaction"],
			as_dict=True,
		)
		self.assertEqual(row.name, draft.name)
		self.assertEqual(row.docstatus, 1)
		self.assertEqual(row.incoming_rate, 100)
		self.assertEqual(row.qty_after_transaction, 8)

	def test_backdated_entry_recomputes_following_balances(self):
		batch = frappe.generate_hash(length=10)
		later = self.make_draft_ledger(
			frappe.generate_hash(length=10),
			qty=10,
			batch_no=batch,
			posting_datetime="2026-07-10 10:00:00",
			submit=True,
		)
		repost_location_balance(
			{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
		)
		self.assertEqual(self.qty_after(later.name), 10)

		# insert an entry dated BEFORE the existing one
		earlier = self.make_draft_ledger(
			frappe.generate_hash(length=10),
			qty=3,
			batch_no=batch,
			posting_datetime="2026-07-05 10:00:00",
			submit=True,
		)
		repost_location_balance(
			{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
		)

		self.assertEqual(self.qty_after(earlier.name), 3)
		self.assertEqual(self.qty_after(later.name), 13)

	def test_balance_isolated_per_batch(self):
		batch_a = frappe.generate_hash(length=10)
		batch_b = frappe.generate_hash(length=10)
		a = self.make_draft_ledger(frappe.generate_hash(length=10), qty=7, batch_no=batch_a, submit=True)
		b = self.make_draft_ledger(frappe.generate_hash(length=10), qty=5, batch_no=batch_b, submit=True)

		for batch in (batch_a, batch_b):
			repost_location_balance(
				{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
			)

		self.assertEqual(self.qty_after(a.name), 7)
		self.assertEqual(self.qty_after(b.name), 5)

	def test_ledger_created_from_stock_ledger_entry(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		batch_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SLL-BCH-.####",
				"valuation_rate": 100,
			}
		).name

		se = make_stock_entry(item_code=batch_item, target="_Test Warehouse - _TC", qty=8, basic_rate=100)

		rows = frappe.get_all(
			"Stock Location Ledger",
			filters={"voucher_no": se.name, "docstatus": 1},
			fields=["batch_no", "qty", "qty_after_transaction", "docstatus", "warehouse"],
		)
		self.assertTrue(rows)
		self.assertEqual(sum(r.qty for r in rows), 8)
		self.assertEqual(rows[0].docstatus, 1)
		self.assertEqual(rows[0].qty_after_transaction, 8)

		se.cancel()
		cancelled = frappe.db.count("Stock Location Ledger", {"voucher_no": se.name, "docstatus": 2})
		self.assertTrue(cancelled)

	def test_voucher_reader_returns_batches(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			get_batches_for_voucher,
		)

		batch_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SLL-RD-.####",
				"valuation_rate": 100,
			}
		).name
		se = make_stock_entry(item_code=batch_item, target="_Test Warehouse - _TC", qty=6, basic_rate=100)

		from_ledger = get_batches_for_voucher(se.doctype, se.name, se.items[0].name, "_Test Warehouse - _TC")

		self.assertEqual(sum(from_ledger.values()), 6)

	def test_voucher_reader_returns_serial_nos(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.doctype.stock_location_ledger.stock_location_ledger import (
			get_serial_nos_for_voucher,
		)

		serial_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SLL-SN-.####",
				"valuation_rate": 100,
			}
		).name
		se = make_stock_entry(item_code=serial_item, target="_Test Warehouse - _TC", qty=3, basic_rate=100)

		from_ledger = get_serial_nos_for_voucher(
			se.doctype, se.name, se.items[0].name, "_Test Warehouse - _TC"
		)

		self.assertEqual(len(from_ledger), 3)

	def test_qty_chain_per_rack_bin_with_shared_valuation(self):
		rack = self.get_or_create_rack("_Test SLL Rack 1")
		bin1 = self.get_or_create_bin("_Test SLL Bin 1", rack)
		bin2 = self.get_or_create_bin("_Test SLL Bin 2", rack)
		batch = frappe.generate_hash(length=10)

		row1 = self.make_draft_ledger(
			frappe.generate_hash(length=10),
			qty=10,
			batch_no=batch,
			rack=rack,
			bin=bin1,
			stock_value_difference=1000,
			submit=True,
		)
		row2 = self.make_draft_ledger(
			frappe.generate_hash(length=10),
			qty=5,
			batch_no=batch,
			rack=rack,
			bin=bin2,
			stock_value_difference=500,
			submit=True,
		)
		row3 = self.make_draft_ledger(
			frappe.generate_hash(length=10),
			qty=-3,
			batch_no=batch,
			rack=rack,
			bin=bin1,
			stock_value_difference=-300,
			submit=True,
		)

		repost_location_balance(
			{"item_code": self.item, "warehouse": "_Test Warehouse - _TC", "batch_no": batch}
		)

		self.assertEqual(self.qty_after(row1.name), 10)
		self.assertEqual(self.qty_after(row2.name), 5)
		self.assertEqual(self.qty_after(row3.name), 7)

		values = [
			frappe.db.get_value("Stock Location Ledger", row.name, "stock_value")
			for row in (row1, row2, row3)
		]
		self.assertEqual(values, [1000, 1500, 1200])

	def test_inline_editor_rack_bin_for_plain_item(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.serial_batch_inline_editor import upsert_bundle_entries

		rack = self.get_or_create_rack("_Test SLL Rack 1")
		bin1 = self.get_or_create_bin("_Test SLL Bin 1", rack)

		se = make_stock_entry(
			item_code=self.item, target="_Test Warehouse - _TC", qty=5, basic_rate=100, do_not_submit=True
		)
		upsert_bundle_entries(
			child_row=se.items[0].as_dict(),
			doc=se.as_dict(),
			entries=[
				{"serial_no": "", "batch_no": "", "rack": rack, "bin": bin1, "qty": 3},
				{"serial_no": "", "batch_no": "", "rack": rack, "bin": "", "qty": 2},
			],
		)

		drafts_keys = frappe.get_all(
			"Stock Location Ledger",
			filters={"voucher_no": se.name, "docstatus": 0},
			fields=["serial_no", "batch_no"],
		)
		for row in drafts_keys:
			self.assertIsNone(row.serial_no)
			self.assertIsNone(row.batch_no)

		drafts = frappe.get_all(
			"Stock Location Ledger",
			filters={"voucher_no": se.name, "docstatus": 0},
			fields=["rack", "bin", "qty"],
		)
		self.assertEqual(len(drafts), 2)
		self.assertEqual({(d.rack, d.bin, d.qty) for d in drafts}, {(rack, bin1, 3.0), (rack, None, 2.0)})

		se.reload()
		se.submit()

		promoted = frappe.get_all(
			"Stock Location Ledger",
			filters={"voucher_no": se.name, "docstatus": 1},
			fields=["rack", "bin", "qty", "qty_after_transaction", "stock_value_difference"],
		)
		self.assertEqual(len(promoted), 2)
		by_spot = {(d.rack, d.bin): d for d in promoted}
		self.assertEqual(by_spot[(rack, bin1)].qty_after_transaction, 3)
		self.assertEqual(by_spot[(rack, None)].qty_after_transaction, 2)
		self.assertEqual(by_spot[(rack, bin1)].stock_value_difference, 300)
		self.assertEqual(by_spot[(rack, None)].stock_value_difference, 200)

	def test_amended_document_prefills_from_cancelled_ledger(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.serial_batch_inline_editor import (
			get_amended_ledger_entries,
			upsert_bundle_entries,
		)

		rack = self.get_or_create_rack("_Test SLL Rack 1")
		bin1 = self.get_or_create_bin("_Test SLL Bin 1", rack)

		se = make_stock_entry(
			item_code=self.item, target="_Test Warehouse - _TC", qty=5, basic_rate=100, do_not_submit=True
		)
		upsert_bundle_entries(
			child_row=se.items[0].as_dict(),
			doc=se.as_dict(),
			entries=[{"rack": rack, "bin": bin1, "qty": 3}, {"rack": rack, "qty": 2}],
		)
		se.reload()
		se.submit()
		se.cancel()

		prefill = get_amended_ledger_entries(
			voucher_type="Stock Entry",
			amended_from=se.name,
			child_doctype="Stock Entry Detail",
			idx=se.items[0].idx,
			warehouse="_Test Warehouse - _TC",
		)
		self.assertEqual({(d.rack, d.bin, d.qty) for d in prefill}, {(rack, bin1, 3.0), (rack, None, 2.0)})

		amended = frappe.copy_doc(se)
		amended.docstatus = 0
		amended.amended_from = se.name
		amended.insert()

		self.assertFalse(frappe.db.exists("Stock Location Ledger", {"voucher_no": amended.name}))

		upsert_bundle_entries(
			child_row=amended.items[0].as_dict(),
			doc=amended.as_dict(),
			entries=prefill,
			replace=1,
		)
		amended.reload()
		amended.submit()

		promoted = frappe.get_all(
			"Stock Location Ledger",
			filters={"voucher_no": amended.name, "docstatus": 1},
			fields=["rack", "bin", "qty_after_transaction"],
		)
		by_spot = {(d.rack, d.bin): d.qty_after_transaction for d in promoted}
		self.assertEqual(by_spot, {(rack, bin1): 3.0, (rack, None): 2.0})

	def test_negative_check_uses_key_total_across_spots(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.serial_batch_inline_editor import upsert_bundle_entries

		rack = self.get_or_create_rack("_Test SLL Rack 1")
		batch_item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SLLRB-.####",
			}
		).name

		receipt = make_stock_entry(
			item_code=batch_item, target="_Test Warehouse - _TC", qty=10, basic_rate=100
		)
		batch_no = frappe.db.get_value(
			"Stock Location Ledger", {"voucher_no": receipt.name, "docstatus": 1}, "batch_no"
		)
		self.assertTrue(batch_no)

		issue = make_stock_entry(
			item_code=batch_item, source="_Test Warehouse - _TC", qty=5, do_not_submit=True
		)
		upsert_bundle_entries(
			child_row=issue.items[0].as_dict(),
			doc=issue.as_dict(),
			entries=[{"batch_no": batch_no, "rack": rack, "qty": 5}],
		)

		issue.reload()
		issue.submit()

		spot_qty = frappe.db.get_value(
			"Stock Location Ledger",
			{"voucher_no": issue.name, "docstatus": 1},
			"qty_after_transaction",
		)
		self.assertEqual(spot_qty, -5)

	def get_or_create_rack(self, rack_name):
		if frappe.db.exists("Rack", rack_name):
			return rack_name
		return (
			frappe.get_doc({"doctype": "Rack", "rack_name": rack_name, "warehouse": "_Test Warehouse - _TC"})
			.insert(ignore_permissions=True)
			.name
		)

	def get_or_create_bin(self, bin_name, rack):
		if frappe.db.exists("Bin", bin_name):
			return bin_name
		return (
			frappe.get_doc({"doctype": "Bin", "bin_name": bin_name, "rack": rack})
			.insert(ignore_permissions=True)
			.name
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"auto_create_serial_batch_entries_for_outward": 1})
	def test_batchwise_valuation_for_same_posting_datetime_entries(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBSPD-SLL1-.#####",
				"valuation_method": "FIFO",
			}
		).name

		warehouse = "_Test Warehouse - _TC"

		receipt = make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=100,
			target=warehouse,
			posting_date=add_days(today(), -5),
			posting_time="12:00:00",
		)

		batch_no = frappe.db.get_value(
			"Stock Location Ledger", {"voucher_no": receipt.name, "docstatus": 1}, "batch_no"
		)
		self.assertTrue(frappe.db.get_value("Batch", batch_no, "use_batchwise_valuation"))

		# same posting datetime as the outward rows below, at a different rate
		make_stock_entry(
			item_code=item_code,
			qty=20,
			rate=250,
			target=warehouse,
			batch_no=batch_no,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
		)

		issue = make_stock_entry(
			item_code=item_code,
			qty=2,
			source=warehouse,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
			do_not_save=True,
		)

		for qty in [3, 4]:
			issue.append(
				"items",
				{
					"item_code": item_code,
					"s_warehouse": warehouse,
					"qty": qty,
					"conversion_factor": 1,
				},
			)

		issue.save()
		issue.submit()

		# (10 * 100 + 20 * 250) / 30 = 200
		self.assert_batchwise_outgoing_rate(item_code, outgoing_rate=200.0, balance_value=4200.0)

		# backdated receipt reposts the same posting datetime cluster
		make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=100,
			target=warehouse,
			batch_no=batch_no,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -4),
			posting_time="12:00:00",
		)

		# (20 * 100 + 20 * 250) / 40 = 175
		self.assert_batchwise_outgoing_rate(item_code, outgoing_rate=175.0, balance_value=5425.0)

	@ERPNextTestSuite.change_settings("Stock Settings", {"auto_create_serial_batch_entries_for_outward": 1})
	def test_batchwise_valuation_when_draft_ledgers_created_before_the_sle(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.serial_batch_inline_editor import upsert_bundle_entries

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBSPD-SLL2-.#####",
				"valuation_method": "FIFO",
			}
		).name

		warehouse = "_Test Warehouse - _TC"

		receipt = make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=100,
			target=warehouse,
			posting_date=add_days(today(), -5),
			posting_time="12:00:00",
		)

		batch_no = frappe.db.get_value(
			"Stock Location Ledger", {"voucher_no": receipt.name, "docstatus": 1}, "batch_no"
		)

		# inward composed as draft ledger rows via the inline editor, before the
		# outward below is submitted - the promotion must restamp their creation
		# so the replay order follows submission, not composition
		inward = make_stock_entry(
			item_code=item_code,
			qty=20,
			rate=200,
			target=warehouse,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
			do_not_submit=True,
		)
		upsert_bundle_entries(
			child_row=inward.items[0].as_dict(),
			doc=inward.as_dict(),
			entries=[{"batch_no": batch_no, "qty": 20}],
		)

		outward = make_stock_entry(
			item_code=item_code,
			qty=10,
			source=warehouse,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
		)

		inward.reload()
		inward.submit()

		outward_sle_creation = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": outward.name, "is_cancelled": 0}, "creation"
		)
		inward_row_creation = frappe.db.get_value(
			"Stock Location Ledger", {"voucher_no": inward.name, "docstatus": 1}, "creation"
		)
		self.assertTrue(get_datetime(inward_row_creation) > get_datetime(outward_sle_creation))

		repost = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": add_days(today(), -6),
				"posting_time": "00:00:00",
				"allow_negative_stock": 1,
			}
		)
		repost.submit()

		# the outward precedes the inward as per the SLE creation even though the
		# inward's ledger rows were composed first
		self.assert_batchwise_outgoing_rate(item_code, outgoing_rate=100.0, balance_value=4000.0)

	def assert_batchwise_outgoing_rate(self, item_code, outgoing_rate, balance_value):
		sl_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_code, "is_cancelled": 0},
			fields=["actual_qty", "stock_value_difference", "stock_value"],
			order_by="posting_datetime, creation",
		)

		for sle in sl_entries:
			if sle.actual_qty > 0:
				continue

			self.assertEqual(flt(sle.stock_value_difference, 2), flt(sle.actual_qty * outgoing_rate, 2))

		self.assertEqual(flt(sl_entries[-1].stock_value, 2), flt(balance_value, 2))
