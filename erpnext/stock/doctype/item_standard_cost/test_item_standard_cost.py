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


def ensure_mfg_variance_account(company):
	"""Ensure `company` has a Default Manufacturing Variance Account so Manufacture/Repack entries of
	Standard Cost finished goods can book the consumed-cost-vs-standard difference."""
	account = frappe.get_cached_value("Company", company, "default_manufacturing_variance_account")
	if account:
		return account

	from erpnext.accounts.doctype.account.test_account import create_account

	# Place it under the same group as the company's default expense account.
	expense_account = frappe.get_cached_value("Company", company, "default_expense_account")
	parent_account = frappe.db.get_value("Account", expense_account, "parent_account")
	account = create_account(
		account_name="Manufacturing Variance",
		account_type="Expense Account",
		parent_account=parent_account,
		company=company,
		account_currency=frappe.get_cached_value("Company", company, "default_currency"),
	)
	frappe.db.set_value("Company", company, "default_manufacturing_variance_account", account)
	return account


class TestItemStandardCost(ERPNextTestSuite):
	def setUp(self):
		ensure_ppv_account(TEST_COMPANY)
		ensure_ppv_account(PI_COMPANY)
		ensure_mfg_variance_account(PI_COMPANY)

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

	def test_cancel_allowed_without_stock_activity(self):
		# No stock transaction on/after the effective date -> the standard cost can be cancelled.
		item = create_standard_cost_item()
		isc = create_item_standard_cost(item.name, rate=100)
		isc.cancel()
		self.assertEqual(isc.docstatus, 2)

	def test_cancel_blocked_with_stock_activity(self):
		# A stock transaction on/after the effective date is valued at this standard rate, so the
		# standard cost cannot be cancelled while it exists.
		item = create_standard_cost_item()
		isc = create_item_standard_cost(item.name, rate=100)
		make_stock_entry(item_code=item.name, target=TEST_WAREHOUSE, qty=5, basic_rate=100)
		self.assertRaises(frappe.ValidationError, isc.cancel)

	def test_cancel_reverses_revaluation(self):
		# Cancelling a rate change reverses the revaluation Stock Reconciliation it created, restoring
		# the previous stock value (the movement that triggered it predates the effective date).
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, effective_date=add_days(today(), -10))
		make_stock_entry(
			item_code=item.name,
			target=TEST_WAREHOUSE,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -5),
		)

		isc2 = create_item_standard_cost(item.name, rate=130, effective_date=today())
		self.assertTrue(isc2.revaluation_entry)

		def stock_value():
			return flt(
				frappe.db.get_value(
					"Bin", {"item_code": item.name, "warehouse": TEST_WAREHOUSE}, "stock_value"
				)
			)

		self.assertEqual(stock_value(), 1300)

		isc2.cancel()
		self.assertEqual(frappe.db.get_value("Stock Reconciliation", isc2.revaluation_entry, "docstatus"), 2)
		self.assertEqual(stock_value(), 1000)

	def test_stock_reconciliation_rate_change_creates_standard_cost(self):
		# Editing the rate on a reconciliation creates a new Item Standard Cost and revalues on-hand
		# stock to it - the reconciliation is a shortcut into the standard cost, not a manual override.
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_item_standard_rate
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		create_item_standard_cost(
			item.name, rate=100, company=PI_COMPANY, effective_date=add_days(today(), -10)
		)
		make_stock_entry(
			item_code=item.name,
			to_warehouse=PI_STORES,
			company=PI_COMPANY,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -5),
		)

		# Same quantity, new rate 130: a new standard cost is set and the 10 on-hand units revalue to 1300.
		reco = create_stock_reconciliation(
			item_code=item.name, warehouse=PI_STORES, qty=10, rate=130, company=PI_COMPANY
		)
		self.assertEqual(reco.docstatus, 1)

		self.assertEqual(flt(get_item_standard_rate(item.name, PI_COMPANY)), 130)
		stock_value = frappe.db.get_value(
			"Bin", {"item_code": item.name, "warehouse": PI_STORES}, "stock_value"
		)
		self.assertEqual(flt(stock_value), 1300)

	def test_stock_reconciliation_qty_change_allowed(self):
		# A reconciliation may adjust the quantity of a Standard Cost item: stock stays valued at the
		# standard rate and the value difference is booked to the Stock Adjustment account.
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=100, company=PI_COMPANY)
		make_stock_entry(
			item_code=item.name, to_warehouse=PI_STORES, company=PI_COMPANY, qty=10, basic_rate=100
		)

		# Count down to 8 at the standard rate: value 800, a 200 reduction against Stock Adjustment.
		reco = create_stock_reconciliation(
			item_code=item.name, warehouse=PI_STORES, qty=8, rate=100, company=PI_COMPANY
		)
		self.assertEqual(reco.docstatus, 1)

		bin_data = frappe.db.get_value(
			"Bin",
			{"item_code": item.name, "warehouse": PI_STORES},
			["actual_qty", "stock_value"],
			as_dict=True,
		)
		self.assertEqual(flt(bin_data.actual_qty), 8)
		self.assertEqual(flt(bin_data.stock_value), 800)

		sle = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": reco.name, "is_cancelled": 0}, "valuation_rate"
		)
		self.assertEqual(flt(sle), 100)

		stock_adjustment = frappe.get_cached_value("Company", PI_COMPANY, "stock_adjustment_account")
		booked = flt(
			frappe.db.sql(
				"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s and is_cancelled=0",
				(reco.name, stock_adjustment),
			)[0][0]
		)
		self.assertEqual(booked, 200)

	def test_opening_reconciliation_creates_standard_cost(self):
		# With no Item Standard Cost yet, an opening Stock Reconciliation may set the rate; that rate is
		# captured into an Item Standard Cost record so the resulting stock (and later transactions) are
		# valued at it.
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import (
			get_item_standard_rate,
			has_item_standard_cost,
		)
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		self.assertFalse(has_item_standard_cost(item.name, PI_COMPANY))

		reco = create_stock_reconciliation(
			item_code=item.name, warehouse=PI_STORES, qty=5, rate=100, company=PI_COMPANY
		)
		self.assertEqual(reco.docstatus, 1)

		# The opening rate is now the item's standard cost.
		self.assertTrue(has_item_standard_cost(item.name, PI_COMPANY))
		self.assertEqual(flt(get_item_standard_rate(item.name, PI_COMPANY)), 100)

		bin_data = frappe.db.get_value(
			"Bin",
			{"item_code": item.name, "warehouse": PI_STORES},
			["actual_qty", "stock_value"],
			as_dict=True,
		)
		self.assertEqual(flt(bin_data.actual_qty), 5)
		self.assertEqual(flt(bin_data.stock_value), 500)

	def test_opening_reconciliation_requires_rate(self):
		# An opening reconciliation for a Standard Cost item with no standard rate yet must carry a
		# positive rate - there is nothing to value the stock at otherwise.
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		self.assertRaises(
			frappe.ValidationError,
			create_stock_reconciliation,
			item_code=item.name,
			warehouse=PI_STORES,
			qty=5,
			rate=0,
			company=PI_COMPANY,
		)

	def test_opening_reconciliation_points_standard_cost_to_itself(self):
		# The captured Item Standard Cost records the reconciliation as its revaluation entry (the reco is
		# the revaluation) instead of spawning a second one.
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		reco = create_stock_reconciliation(
			item_code=item.name, warehouse=PI_STORES, qty=5, rate=100, company=PI_COMPANY
		)

		isc = frappe.db.get_value(
			"Item Standard Cost",
			{"item_code": item.name, "company": PI_COMPANY, "docstatus": 1},
			"revaluation_entry",
		)
		self.assertEqual(isc, reco.name)

	def test_opening_reconciliation_cancel_cancels_standard_cost(self):
		# Cancelling an opening reconciliation removes the stock it created, so the Item Standard Cost it
		# introduced is cancelled too.
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import has_item_standard_cost
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		reco = create_stock_reconciliation(
			item_code=item.name, warehouse=PI_STORES, qty=5, rate=100, company=PI_COMPANY
		)
		isc_name = frappe.db.get_value(
			"Item Standard Cost", {"item_code": item.name, "company": PI_COMPANY, "docstatus": 1}, "name"
		)

		reco.cancel()

		self.assertEqual(frappe.db.get_value("Item Standard Cost", isc_name, "docstatus"), 2)
		self.assertFalse(has_item_standard_cost(item.name, PI_COMPANY))

	def test_rate_change_reconciliation_cancel_reverts_standard_cost(self):
		# A rate-change reconciliation revalues on-hand stock only on/after its effective date, and that
		# revaluation is reversed on cancel. The pre-existing stock sits before the effective date, so no
		# live SLE is valued at the new rate once the reco's own entry is reversed. Cancelling therefore
		# cancels the Item Standard Cost it created and the item falls back to the previous standard rate.
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import get_item_standard_rate
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = create_standard_cost_item()
		create_item_standard_cost(
			item.name, rate=100, company=PI_COMPANY, effective_date=add_days(today(), -10)
		)
		make_stock_entry(
			item_code=item.name,
			to_warehouse=PI_STORES,
			company=PI_COMPANY,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -5),
		)

		reco = create_stock_reconciliation(
			item_code=item.name, warehouse=PI_STORES, qty=10, rate=130, company=PI_COMPANY
		)
		isc_name = frappe.db.get_value("Item Standard Cost", {"revaluation_entry": reco.name}, "name")
		self.assertTrue(isc_name)
		self.assertEqual(flt(get_item_standard_rate(item.name, PI_COMPANY)), 130)

		reco.cancel()

		# The revaluation is reverted, so the standard cost it created is cancelled and the rate reverts.
		self.assertEqual(frappe.db.get_value("Item Standard Cost", isc_name, "docstatus"), 2)
		self.assertEqual(flt(get_item_standard_rate(item.name, PI_COMPANY)), 100)

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

	def test_manufacturing_variance_books_to_variance_account(self):
		# RM standard 50, FG standard 200. Consuming 5 RM (250) to produce 1 FG (200) leaves a
		# 50 (unfavorable) manufacturing variance, which must land in the company's Manufacturing
		# Variance account, not the generic Stock Adjustment account.
		mfg_variance = ensure_mfg_variance_account(PI_COMPANY)
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

		def gl_net(account):
			return flt(
				frappe.db.sql(
					"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s",
					(se.name, account),
				)[0][0]
			)

		# The 50 variance is reclassified to the Manufacturing Variance account...
		self.assertEqual(gl_net(mfg_variance), 50)
		# ...leaving the generic Stock Adjustment account untouched.
		stock_adj = frappe.get_cached_value("Company", PI_COMPANY, "stock_adjustment_account")
		self.assertEqual(gl_net(stock_adj), 0)

	def test_manufacturing_variance_includes_additional_costs(self):
		# The variance is (full consumed cost - standard value), where consumed cost includes prorated
		# additional costs. RM 5 x 50 = 250 plus a 30 additional cost = 280 consumed to make 1 FG valued
		# at its standard 200 -> variance must be 280 - 200 = 80 (not 50).
		mfg_variance = ensure_mfg_variance_account(PI_COMPANY)
		additional_cost_account = "Expenses Included In Valuation - TCP1"
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
		se.append(
			"additional_costs",
			{"expense_account": additional_cost_account, "description": "Freight", "amount": 30},
		)
		se.insert()
		se.submit()

		# FG is still valued at its own standard, regardless of the extra consumed cost.
		fg_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name, "item_code": fg.name, "is_cancelled": 0},
			["valuation_rate", "stock_value_difference"],
			as_dict=True,
		)
		self.assertEqual(flt(fg_sle.valuation_rate), 200)
		self.assertEqual(flt(fg_sle.stock_value_difference), 200)

		def gl_net(account):
			return flt(
				frappe.db.sql(
					"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s",
					(se.name, account),
				)[0][0]
			)

		# Raw material (250) + additional cost (30) - standard value (200) = 80 to Manufacturing Variance.
		self.assertEqual(gl_net(mfg_variance), 80)
		# The additional cost is credited out of its source account (it flowed into the variance).
		self.assertEqual(gl_net(additional_cost_account), -30)

	def test_manufacturing_variance_no_stock_adjustment_entry(self):
		# With an additional cost in the mix, the net-zero Stock Adjustment reclassification must not
		# survive as a debit == credit entry: only the real accounts (variance, additional cost source,
		# stock) should be booked.
		ensure_mfg_variance_account(PI_COMPANY)
		additional_cost_account = "Expenses Included In Valuation - TCP1"
		stock_adjustment = frappe.get_cached_value("Company", PI_COMPANY, "stock_adjustment_account")
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
		se.append(
			"additional_costs",
			{"expense_account": additional_cost_account, "description": "Freight", "amount": 30},
		)
		se.insert()
		se.submit()

		# No Stock Adjustment entry at all - the difference is entirely the manufacturing variance.
		self.assertFalse(
			frappe.db.exists(
				"GL Entry", {"voucher_no": se.name, "account": stock_adjustment, "is_cancelled": 0}
			)
		)

	def test_manufacturing_variance_account_required(self):
		# Without a Manufacturing Variance account, submitting a Standard Cost Manufacture/Repack must fail.
		previous = frappe.get_cached_value("Company", PI_COMPANY, "default_manufacturing_variance_account")
		frappe.db.set_value("Company", PI_COMPANY, "default_manufacturing_variance_account", None)
		frappe.clear_cache(doctype="Company")
		try:
			rm = create_standard_cost_item()
			fg = create_standard_cost_item()
			create_item_standard_cost(rm.name, rate=50, company=PI_COMPANY)
			create_item_standard_cost(fg.name, rate=200, company=PI_COMPANY)
			make_stock_entry(
				item_code=rm.name, to_warehouse=PI_STORES, company=PI_COMPANY, qty=10, basic_rate=50
			)

			se = frappe.new_doc("Stock Entry")
			se.purpose = "Repack"
			se.stock_entry_type = "Repack"
			se.company = PI_COMPANY
			se.append("items", {"item_code": rm.name, "s_warehouse": PI_STORES, "qty": 5})
			se.append("items", {"item_code": fg.name, "t_warehouse": PI_FG, "qty": 1, "is_finished_item": 1})
			se.insert()
			self.assertRaises(frappe.ValidationError, se.submit)
		finally:
			frappe.db.set_value("Company", PI_COMPANY, "default_manufacturing_variance_account", previous)
			frappe.clear_cache(doctype="Company")

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

	def test_pi_without_update_stock_does_not_rebook_variance(self):
		# The Purchase Receipt already booked the 70 variance to PPV. Billing it with a Purchase Invoice
		# that has Update Stock disabled must only clear "Stock Received But Not Billed" at the full billed
		# amount (200) - it must NOT re-book the variance to the Purchase Price Variance account.
		from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		ppv_account = ensure_ppv_account(PI_COMPANY)
		srbnb_account = frappe.get_cached_value("Company", PI_COMPANY, "stock_received_but_not_billed")

		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=130, company=PI_COMPANY)

		pr = make_purchase_receipt(
			item_code=item.name, company=PI_COMPANY, warehouse=PI_STORES, qty=1, rate=200
		)

		pi = make_purchase_invoice(pr.name)
		self.assertEqual(pi.update_stock, 0)
		pi.submit()

		def booked(account):
			return flt(
				frappe.db.sql(
					"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s and is_cancelled=0",
					(pi.name, account),
				)[0][0]
			)

		# No variance re-booked on the invoice; SRBNB is fully cleared at the billed value.
		self.assertEqual(booked(ppv_account), 0)
		self.assertEqual(booked(srbnb_account), 200)

	def test_material_receipt_books_variance_to_ppv(self):
		# Receiving a Standard Cost item via Material Receipt at a manual basic rate (200) plus an
		# additional cost (100) must value stock at the standard 130 and book the rest to the Purchase
		# Price Variance account: (200*10 + 100) - 130*10 = 800.
		ppv_account = ensure_ppv_account(PI_COMPANY)
		additional_cost_account = "Expenses Included In Valuation - TCP1"
		item = create_standard_cost_item()
		create_item_standard_cost(item.name, rate=130, company=PI_COMPANY)

		se = frappe.new_doc("Stock Entry")
		se.purpose = "Material Receipt"
		se.stock_entry_type = "Material Receipt"
		se.company = PI_COMPANY
		se.append(
			"items",
			{
				"item_code": item.name,
				"t_warehouse": PI_STORES,
				"qty": 10,
				"basic_rate": 200,
			},
		)
		se.append(
			"additional_costs",
			{"expense_account": additional_cost_account, "description": "Freight", "amount": 100},
		)
		se.insert()
		se.submit()

		# Stock is valued at the standard rate, not the manual 200 + additional cost.
		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name, "is_cancelled": 0},
			["valuation_rate", "stock_value_difference"],
			as_dict=True,
		)
		self.assertEqual(flt(sle.valuation_rate), 130)
		self.assertEqual(flt(sle.stock_value_difference), 1300)

		def booked(account):
			return flt(
				frappe.db.sql(
					"select sum(debit - credit) from `tabGL Entry` where voucher_no=%s and account=%s and is_cancelled=0",
					(se.name, account),
				)[0][0]
			)

		self.assertEqual(booked(ppv_account), 800)

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
