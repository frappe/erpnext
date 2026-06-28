# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, flt, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

TEST_COMPANY = "_Test Company"
TEST_WAREHOUSE = "_Test Warehouse - _TC"

# Perpetual-inventory company, needed to assert stock GL entries.
PI_COMPANY = "_Test Company with perpetual inventory"
PI_STORES = "Stores - TCP1"
PI_FG = "Finished Goods - TCP1"


def create_standard_cost_item(**properties):
	props = {"valuation_method": "Standard Cost", "is_stock_item": 1, "is_purchase_item": 1}
	props.update(properties)
	return make_item(properties=props)


def create_item_standard_cost(item_code, rate, company=TEST_COMPANY, effective_date=None, submit=True):
	doc = frappe.new_doc("Item Standard Cost")
	doc.item_code = item_code
	doc.company = company
	doc.standard_rate = rate
	doc.effective_date = effective_date or today()
	doc.insert()
	if submit:
		doc.submit()
	return doc


def ensure_ppv_account(company):
	"""Ensure `company` has a Default Purchase Price Variance Account so receipts/invoices of
	Standard Cost items can book the receipt-rate-vs-standard difference."""
	account = frappe.get_cached_value("Company", company, "default_purchase_price_variance_account")
	if account:
		return account

	from erpnext.accounts.doctype.account.test_account import create_account

	# Place it under the same group as the company's default expense account.
	expense_account = frappe.get_cached_value("Company", company, "default_expense_account")
	parent_account = frappe.db.get_value("Account", expense_account, "parent_account")
	account = create_account(
		account_name="Purchase Price Variance",
		account_type="Expense Account",
		parent_account=parent_account,
		company=company,
		account_currency=frappe.get_cached_value("Company", company, "default_currency"),
	)
	frappe.db.set_value("Company", company, "default_purchase_price_variance_account", account)
	return account


class TestItemStandardCost(ERPNextTestSuite):
	def setUp(self):
		ensure_ppv_account(TEST_COMPANY)
		ensure_ppv_account(PI_COMPANY)

	def test_only_for_standard_cost_items(self):
		item = make_item(properties={"valuation_method": "FIFO", "is_stock_item": 1})
		isc = frappe.new_doc("Item Standard Cost")
		isc.item_code = item.name
		isc.company = TEST_COMPANY
		isc.standard_rate = 100
		self.assertRaises(frappe.ValidationError, isc.insert)

	def test_item_link_query_lists_only_standard_cost_items(self):
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_standard_cost_items

		sc_item = create_standard_cost_item().name
		fifo_item = make_item(properties={"valuation_method": "FIFO", "is_stock_item": 1}).name

		def listed(item_code):
			rows = get_standard_cost_items("Item", item_code, "name", 0, 20, {"company": TEST_COMPANY})
			return item_code in [row[0] for row in rows]

		self.assertTrue(listed(sc_item))
		self.assertFalse(listed(fifo_item))

	def test_rate_must_be_positive(self):
		item = create_standard_cost_item()
		isc = frappe.new_doc("Item Standard Cost")
		isc.item_code = item.name
		isc.company = TEST_COMPANY
		isc.standard_rate = 0
		self.assertRaises(frappe.ValidationError, isc.insert)

	def test_future_effective_date_blocked(self):
		item = create_standard_cost_item()
		isc = frappe.new_doc("Item Standard Cost")
		isc.item_code = item.name
		isc.company = TEST_COMPANY
		isc.standard_rate = 100
		isc.effective_date = add_days(today(), 5)
		self.assertRaises(frappe.ValidationError, isc.insert)

	def test_first_record_requires_no_stock_ledger_entry(self):
		# An item that already has stock movement cannot be moved onto Standard Cost retroactively.
		item = make_item(properties={"valuation_method": "FIFO", "is_stock_item": 1})
		make_stock_entry(item_code=item.name, target=TEST_WAREHOUSE, qty=5, basic_rate=100)

		# Force the method at the db level (the Item-level guard would otherwise block enabling
		# Standard Cost while stock exists) and drop the cached valuation method.
		frappe.db.set_value("Item", item.name, "valuation_method", "Standard Cost")
		frappe.local.request_cache.clear()

		isc = frappe.new_doc("Item Standard Cost")
		isc.item_code = item.name
		isc.company = TEST_COMPANY
		isc.standard_rate = 100
		self.assertRaises(frappe.ValidationError, isc.insert)

	def test_receipt_valued_at_standard(self):
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100)

		# Receive at a different (billed) rate; the ledger must still value at the standard 100.
		se = make_stock_entry(item_code=item.name, target=TEST_WAREHOUSE, qty=10, basic_rate=150)

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": se.name, "is_cancelled": 0},
			fields=["valuation_rate", "stock_value", "incoming_rate"],
		)[0]
		self.assertEqual(flt(sle.valuation_rate), 100)
		self.assertEqual(flt(sle.stock_value), 1000)
		self.assertEqual(flt(sle.incoming_rate), 100)

	def test_rate_change_revalues_on_hand_stock(self):
		# Effective dates must strictly increase, so stage the rate change on a later date.
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, effective_date=add_days(today(), -10))
		make_stock_entry(
			item_code=item.name,
			target=TEST_WAREHOUSE,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -5),
		)

		isc = create_item_standard_cost(item.name, rate=130, effective_date=today())

		# Submitting the new rate must auto-create and submit a revaluation Stock Reconciliation.
		self.assertTrue(isc.revaluation_entry)
		reco_status = frappe.db.get_value("Stock Reconciliation", isc.revaluation_entry, "docstatus")
		self.assertEqual(reco_status, 1)

		stock_value = frappe.db.get_value(
			"Bin", {"item_code": item.name, "warehouse": TEST_WAREHOUSE}, "stock_value"
		)
		self.assertEqual(flt(stock_value), 1300)

	def test_backdated_entry_fast_qty_repost(self):
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, effective_date=add_days(today(), -10))

		se1 = make_stock_entry(
			item_code=item.name,
			target=TEST_WAREHOUSE,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -5),
		)
		se2 = make_stock_entry(
			item_code=item.name,
			target=TEST_WAREHOUSE,
			qty=5,
			basic_rate=100,
			posting_date=add_days(today(), -2),
		)
		se0 = make_stock_entry(
			item_code=item.name,
			target=TEST_WAREHOUSE,
			qty=20,
			basic_rate=100,
			posting_date=add_days(today(), -7),
		)

		def sle(se):
			return frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_no": se.name, "is_cancelled": 0},
				["qty_after_transaction", "stock_value"],
				as_dict=True,
			)

		self.assertEqual(flt(sle(se0).qty_after_transaction), 20)
		self.assertEqual(flt(sle(se1).qty_after_transaction), 30)
		self.assertEqual(flt(sle(se2).qty_after_transaction), 35)
		self.assertEqual(flt(sle(se1).stock_value), 3000)
		self.assertEqual(flt(sle(se2).stock_value), 3500)

		bin_data = frappe.db.get_value(
			"Bin",
			{"item_code": item.name, "warehouse": TEST_WAREHOUSE},
			["actual_qty", "stock_value"],
			as_dict=True,
		)
		self.assertEqual(flt(bin_data.actual_qty), 35)
		self.assertEqual(flt(bin_data.stock_value), 3500)

		self.assertFalse(frappe.db.exists("Repost Item Valuation", {"voucher_no": se0.name}))

	def test_cannot_cancel(self):
		item = create_standard_cost_item()
		isc = create_item_standard_cost(item.name, rate=100)
		self.assertRaises(frappe.ValidationError, isc.cancel)

	def test_direct_stock_reconciliation_blocked(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100)
		make_stock_entry(item_code=item.name, target=TEST_WAREHOUSE, qty=10, basic_rate=100)

		self.assertRaises(
			frappe.ValidationError,
			create_stock_reconciliation,
			item_code=item.name,
			warehouse=TEST_WAREHOUSE,
			qty=8,
			rate=120,
		)

	def test_backdated_transaction_blocked(self):
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, effective_date=today())

		# R2 is enforced when the stock ledger entries are written, i.e. at submit time.
		se = make_stock_entry(
			item_code=item.name,
			target=TEST_WAREHOUSE,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -3),
			do_not_submit=True,
		)
		self.assertRaises(frappe.ValidationError, se.submit)

	def test_manufacturing_variance_books_to_stock_adjustment(self):
		# RM standard 50, FG standard 200. Consuming 5 RM (250) to produce 1 FG (200) leaves a
		# 50 manufacturing variance, which must land in the company's Stock Adjustment account.
		rm = create_standard_cost_item()
		fg = create_standard_cost_item()
		create_item_standard_cost(rm.name, rate=50, company=PI_COMPANY)
		create_item_standard_cost(fg.name, rate=200, company=PI_COMPANY)

		make_stock_entry(item_code=rm.name, to_warehouse=PI_STORES, company=PI_COMPANY, qty=10, basic_rate=50)

		se = frappe.new_doc("Stock Entry")
		se.purpose = "Repack"
		se.stock_entry_type = "Repack"
		se.company = PI_COMPANY
		se.append("items", {"item_code": rm.name, "s_warehouse": PI_STORES, "qty": 5})
		se.append("items", {"item_code": fg.name, "t_warehouse": PI_FG, "qty": 1, "is_finished_item": 1})
		se.insert()
		se.submit()

		# FG is valued at its own standard, not the rolled-up RM cost.
		fg_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name, "item_code": fg.name, "is_cancelled": 0},
			["valuation_rate", "stock_value_difference"],
			as_dict=True,
		)
		self.assertEqual(flt(fg_sle.valuation_rate), 200)
		self.assertEqual(flt(fg_sle.stock_value_difference), 200)

		stock_adj = frappe.get_cached_value("Company", PI_COMPANY, "stock_adjustment_account")
		net = frappe.db.sql(
			"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s",
			(se.name, stock_adj),
		)[0][0]
		self.assertEqual(flt(net), 50)

	def test_valuation_method_change_blocked_with_stock(self):
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100)
		make_stock_entry(item_code=item.name, target=TEST_WAREHOUSE, qty=10, basic_rate=100)

		item.reload()
		item.valuation_method = "FIFO"
		self.assertRaises(frappe.ValidationError, item.save)

	def test_batched_item_revalued_across_warehouses(self):
		# A rate change must revalue a batched Standard Cost item in every warehouse, posted as a
		# pure value change without a serial/batch bundle.
		item = create_standard_cost_item(
			has_batch_no=1, create_new_batch=1, batch_number_series="SC-BATCH-.####"
		)
		create_item_standard_cost(
			item.name, rate=100, company=PI_COMPANY, effective_date=add_days(today(), -5)
		)

		make_stock_entry(
			item_code=item.name,
			to_warehouse=PI_STORES,
			company=PI_COMPANY,
			qty=3,
			basic_rate=100,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
		)
		make_stock_entry(
			item_code=item.name,
			to_warehouse=PI_FG,
			company=PI_COMPANY,
			qty=2,
			basic_rate=100,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
		)

		isc = create_item_standard_cost(item.name, rate=150, company=PI_COMPANY, effective_date=today())
		self.assertTrue(isc.revaluation_entry)

		for warehouse, qty in ((PI_STORES, 3), (PI_FG, 2)):
			stock_value = frappe.db.get_value(
				"Bin", {"item_code": item.name, "warehouse": warehouse}, "stock_value"
			)
			self.assertEqual(flt(stock_value), qty * 150)

	def test_serialized_item_revalued_across_warehouses(self):
		item = create_standard_cost_item(has_serial_no=1, serial_no_series="SC-SER-.####")
		create_item_standard_cost(
			item.name, rate=100, company=PI_COMPANY, effective_date=add_days(today(), -5)
		)

		make_stock_entry(
			item_code=item.name,
			to_warehouse=PI_STORES,
			company=PI_COMPANY,
			qty=3,
			basic_rate=100,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
		)
		make_stock_entry(
			item_code=item.name,
			to_warehouse=PI_FG,
			company=PI_COMPANY,
			qty=2,
			basic_rate=100,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
		)

		isc = create_item_standard_cost(item.name, rate=150, company=PI_COMPANY, effective_date=today())
		self.assertTrue(isc.revaluation_entry)

		for warehouse, qty in ((PI_STORES, 3), (PI_FG, 2)):
			stock_value = frappe.db.get_value(
				"Bin", {"item_code": item.name, "warehouse": warehouse}, "stock_value"
			)
			self.assertEqual(flt(stock_value), qty * 150)

	def test_standard_rate_cache_invalidated_after_submit(self):
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_item_standard_rate

		item = create_standard_cost_item()

		# Read (and request-cache) the rate before any Item Standard Cost exists.
		self.assertIsNone(get_item_standard_rate(item.name, TEST_COMPANY))

		create_item_standard_cost(item.name, rate=100)

		# The submit must have invalidated the cache, so this reads the freshly submitted rate.
		self.assertEqual(flt(get_item_standard_rate(item.name, TEST_COMPANY)), 100)

	def test_pr_stock_value_excludes_rejected_warehouse(self):
		# Accepted and rejected stock for one receipt row share voucher_detail_no. The standard-cost
		# SRBNB split must clear only the accepted warehouse's value, not accepted + rejected.
		from erpnext.accounts.doctype.purchase_invoice.services.gl_composer import (
			PurchaseInvoiceGLComposer,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, company=PI_COMPANY)

		rejected_warehouse = create_warehouse("_Test SC Rejected Warehouse", company=PI_COMPANY)

		# Receive 10 accepted + 2 rejected at a billed rate of 150; both SLEs value at the standard 100.
		pr = make_purchase_receipt(
			item_code=item.name,
			company=PI_COMPANY,
			warehouse=PI_STORES,
			qty=10,
			rejected_qty=2,
			rejected_warehouse=rejected_warehouse,
			rate=150,
		)

		# Method body uses only `item`, so it can be called unbound.
		def pr_value(stock_qty):
			mock_item = frappe._dict(
				purchase_receipt=pr.name, pr_detail=pr.items[0].name, stock_qty=stock_qty
			)
			return flt(PurchaseInvoiceGLComposer.get_pr_stock_value(None, mock_item))

		# Billing all 10: accepted only (10 * 100), not accepted + rejected (12 * 100).
		self.assertEqual(pr_value(10), 1000)
		# Billing only 4 of the 10 accepted units: pro-rated to the invoiced qty (4 * 100).
		self.assertEqual(pr_value(4), 400)

	def test_pr_books_variance_to_ppv_account(self):
		# Receiving a Standard Cost item at a rate above the standard must book the difference to the
		# Purchase Price Variance account, not the default expense (COGS) account.
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		ppv_account = ensure_ppv_account(PI_COMPANY)
		cogs_account = frappe.get_cached_value("Company", PI_COMPANY, "default_expense_account")

		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=130, company=PI_COMPANY)

		# Receive 1 @ 200: stock booked at standard 130, the 70 difference is the purchase price variance.
		pr = make_purchase_receipt(
			item_code=item.name, company=PI_COMPANY, warehouse=PI_STORES, qty=1, rate=200
		)

		def booked(account):
			return flt(
				frappe.db.sql(
					"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s and is_cancelled=0",
					(pr.name, account),
				)[0][0]
			)

		self.assertEqual(booked(ppv_account), 70)
		self.assertEqual(booked(cogs_account), 0)

	def test_pr_throws_without_ppv_account(self):
		# Receiving a Standard Cost item with a variance but no PPV account configured must error.
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		previous = frappe.get_cached_value("Company", PI_COMPANY, "default_purchase_price_variance_account")
		frappe.db.set_value("Company", PI_COMPANY, "default_purchase_price_variance_account", None)
		frappe.clear_cache(doctype="Company")
		try:
			item = create_standard_cost_item()
			create_item_standard_cost(item.name, rate=130, company=PI_COMPANY)
			self.assertRaises(
				frappe.ValidationError,
				make_purchase_receipt,
				item_code=item.name,
				company=PI_COMPANY,
				warehouse=PI_STORES,
				qty=1,
				rate=200,
			)
		finally:
			frappe.db.set_value("Company", PI_COMPANY, "default_purchase_price_variance_account", previous)
			frappe.clear_cache(doctype="Company")

	def test_revaluation_posted_after_same_day_movement(self):
		# A movement earlier on the effective date must not end up after the revaluation, otherwise the
		# reco would backdate the current quantity ahead of it.
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, effective_date=add_days(today(), -2))

		se = make_stock_entry(
			item_code=item.name, target=TEST_WAREHOUSE, qty=10, basic_rate=100, posting_date=today()
		)

		isc = create_item_standard_cost(item.name, rate=150, effective_date=today())

		reco_time = frappe.db.get_value("Stock Reconciliation", isc.revaluation_entry, "posting_time")
		se_time = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": se.name, "is_cancelled": 0}, "posting_time"
		)
		self.assertGreaterEqual(str(reco_time), str(se_time))

		stock_value = frappe.db.get_value(
			"Bin", {"item_code": item.name, "warehouse": TEST_WAREHOUSE}, "stock_value"
		)
		self.assertEqual(flt(stock_value), 1500)
