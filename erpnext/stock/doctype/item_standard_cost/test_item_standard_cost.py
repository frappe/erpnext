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


class TestItemStandardCost(ERPNextTestSuite):
	def test_only_for_standard_cost_items(self):
		item = make_item(properties={"valuation_method": "FIFO", "is_stock_item": 1})
		isc = frappe.new_doc("Item Standard Cost")
		isc.item_code = item.name
		isc.company = TEST_COMPANY
		isc.standard_rate = 100
		self.assertRaises(frappe.ValidationError, isc.insert)

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
