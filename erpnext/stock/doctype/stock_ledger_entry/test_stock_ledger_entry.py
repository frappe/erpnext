# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from uuid import uuid4

import frappe
from frappe.core.page.permission_manager.permission_manager import reset
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.query_builder.functions import CombineDatetime
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, add_to_date, flt, today

from erpnext.accounts.doctype.gl_entry.gl_entry import rename_gle_sle_docs
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
	create_landed_cost_voucher,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import BackDatedStockTransaction
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.stock.tests.test_utils import StockTestMixin


class TestStockLedgerEntry(FrappeTestCase, StockTestMixin):
	def setUp(self):
		items = create_items()
		reset("Stock Entry")

		# delete SLE and BINs for all items
		frappe.db.sql(
			"delete from `tabStock Ledger Entry` where item_code in (%s)"
			% (", ".join(["%s"] * len(items))),
			items,
		)
		frappe.db.sql(
			"delete from `tabBin` where item_code in (%s)" % (", ".join(["%s"] * len(items))), items
		)

	def tearDown(self):
		frappe.db.rollback()

	def test_item_cost_reposting(self):
		company = "_Test Company"

		# _Test Item for Reposting at Stores warehouse on 10-04-2020: Qty = 50, Rate = 100
		create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - _TC",
			qty=50,
			rate=100,
			company=company,
			expense_account="Stock Adjustment - _TC"
			if frappe.get_all("Stock Ledger Entry")
			else "Temporary Opening - _TC",
			posting_date="2020-04-10",
			posting_time="14:00",
		)

		# _Test Item for Reposting at FG warehouse on 20-04-2020: Qty = 10, Rate = 200
		create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Finished Goods - _TC",
			qty=10,
			rate=200,
			company=company,
			expense_account="Stock Adjustment - _TC"
			if frappe.get_all("Stock Ledger Entry")
			else "Temporary Opening - _TC",
			posting_date="2020-04-20",
			posting_time="14:00",
		)

		# _Test Item for Reposting transferred from Stores to FG warehouse on 30-04-2020
		se = make_stock_entry(
			item_code="_Test Item for Reposting",
			source="Stores - _TC",
			target="Finished Goods - _TC",
			company=company,
			qty=10,
			expense_account="Stock Adjustment - _TC"
			if frappe.get_all("Stock Ledger Entry")
			else "Temporary Opening - _TC",
			posting_date="2020-04-30",
			posting_time="14:00",
		)
		target_wh_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"item_code": "_Test Item for Reposting",
				"warehouse": "Finished Goods - _TC",
				"voucher_type": "Stock Entry",
				"voucher_no": se.name,
			},
			["valuation_rate"],
			as_dict=1,
		)

		self.assertEqual(target_wh_sle.get("valuation_rate"), 150)

		# Repack entry on 5-5-2020
		repack = create_repack_entry(company=company, posting_date="2020-05-05", posting_time="14:00")

		finished_item_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"item_code": "_Test Finished Item for Reposting",
				"warehouse": "Finished Goods - _TC",
				"voucher_type": "Stock Entry",
				"voucher_no": repack.name,
			},
			["incoming_rate", "valuation_rate"],
			as_dict=1,
		)
		self.assertEqual(finished_item_sle.get("incoming_rate"), 540)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 540)

		# Reconciliation for _Test Item for Reposting at Stores on 12-04-2020: Qty = 50, Rate = 150
		sr = create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - _TC",
			qty=50,
			rate=150,
			company=company,
			expense_account="Stock Adjustment - _TC"
			if frappe.get_all("Stock Ledger Entry")
			else "Temporary Opening - _TC",
			posting_date="2020-04-12",
			posting_time="14:00",
		)

		# Check valuation rate of finished goods warehouse after back-dated entry at Stores
		target_wh_sle = get_previous_sle(
			{
				"item_code": "_Test Item for Reposting",
				"warehouse": "Finished Goods - _TC",
				"posting_date": "2020-04-30",
				"posting_time": "14:00",
			}
		)
		self.assertEqual(target_wh_sle.get("incoming_rate"), 150)
		self.assertEqual(target_wh_sle.get("valuation_rate"), 175)

		# Check valuation rate of repacked item after back-dated entry at Stores
		finished_item_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"item_code": "_Test Finished Item for Reposting",
				"warehouse": "Finished Goods - _TC",
				"voucher_type": "Stock Entry",
				"voucher_no": repack.name,
			},
			["incoming_rate", "valuation_rate"],
			as_dict=1,
		)
		self.assertEqual(finished_item_sle.get("incoming_rate"), 790)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 790)

		# Check updated rate in Repack entry
		repack.reload()
		self.assertEqual(repack.items[0].get("basic_rate"), 150)
		self.assertEqual(repack.items[1].get("basic_rate"), 750)

	def test_purchase_return_valuation_reposting(self):
		pr = make_purchase_receipt(
			company="_Test Company",
			posting_date="2020-04-10",
			warehouse="Stores - _TC",
			item_code="_Test Item for Reposting",
			qty=5,
			rate=100,
		)

		return_pr = make_purchase_receipt(
			company="_Test Company",
			posting_date="2020-04-15",
			warehouse="Stores - _TC",
			item_code="_Test Item for Reposting",
			is_return=1,
			return_against=pr.name,
			qty=-2,
		)

		# check sle
		outgoing_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": return_pr.name},
			["outgoing_rate", "stock_value_difference"],
		)

		self.assertEqual(outgoing_rate, 100)
		self.assertEqual(stock_value_difference, -200)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		outgoing_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": return_pr.name},
			["outgoing_rate", "stock_value_difference"],
		)

		self.assertEqual(outgoing_rate, 110)
		self.assertEqual(stock_value_difference, -220)

	def test_sales_return_valuation_reposting(self):
		company = "_Test Company"
		item_code = "_Test Item for Reposting"

		# Purchase Return: Qty = 5, Rate = 100
		pr = make_purchase_receipt(
			company=company,
			posting_date="2020-04-10",
			warehouse="Stores - _TC",
			item_code=item_code,
			qty=5,
			rate=100,
		)

		# Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(
			item_code=item_code,
			qty=5,
			rate=150,
			warehouse="Stores - _TC",
			company=company,
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
		)

		# check outgoing_rate for DN
		outgoing_rate = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name},
				"stock_value_difference",
			)
			/ 5
		)

		self.assertEqual(dn.items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(
			is_return=1,
			return_against=dn.name,
			item_code=item_code,
			qty=-2,
			rate=150,
			company=company,
			warehouse="Stores - _TC",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
		)

		# check incoming rate for Return entry
		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(return_dn.items[0].incoming_rate, 100)
		self.assertEqual(incoming_rate, 100)
		self.assertEqual(stock_value_difference, 200)

		# -------------------------------

		# Landed Cost Voucher to update the rate of incoming Purchase Return: Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# check outgoing_rate for DN after reposting
		outgoing_rate = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name},
				"stock_value_difference",
			)
			/ 5
		)
		self.assertEqual(outgoing_rate, 110)

		dn.reload()
		self.assertEqual(dn.items[0].incoming_rate, 110)

		# check incoming rate for Return entry after reposting
		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(incoming_rate, 110)
		self.assertEqual(stock_value_difference, 220)

		return_dn.reload()
		self.assertEqual(return_dn.items[0].incoming_rate, 110)

		# Cleanup data
		return_dn.cancel()
		dn.cancel()
		lcv.cancel()
		pr.cancel()

	def test_reposting_of_sales_return_for_packed_item(self):
		company = "_Test Company"
		packed_item_code = "_Test Item for Reposting"
		bundled_item = "_Test Bundled Item for Reposting"
		create_product_bundle_item(bundled_item, [[packed_item_code, 4]])

		# Purchase Return: Qty = 50, Rate = 100
		pr = make_purchase_receipt(
			company=company,
			posting_date="2020-04-10",
			warehouse="Stores - _TC",
			item_code=packed_item_code,
			qty=50,
			rate=100,
		)

		# Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(
			item_code=bundled_item,
			qty=5,
			rate=150,
			warehouse="Stores - _TC",
			company=company,
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
		)

		# check outgoing_rate for DN
		outgoing_rate = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name},
				"stock_value_difference",
			)
			/ 20
		)

		self.assertEqual(dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(
			is_return=1,
			return_against=dn.name,
			item_code=bundled_item,
			qty=-2,
			rate=150,
			company=company,
			warehouse="Stores - _TC",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
		)

		# check incoming rate for Return entry
		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(return_dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(incoming_rate, 100)
		self.assertEqual(stock_value_difference, 800)

		# -------------------------------

		# Landed Cost Voucher to update the rate of incoming Purchase Return: Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# check outgoing_rate for DN after reposting
		outgoing_rate = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name},
				"stock_value_difference",
			)
			/ 20
		)
		self.assertEqual(outgoing_rate, 101)

		dn.reload()
		self.assertEqual(dn.packed_items[0].incoming_rate, 101)

		# check incoming rate for Return entry after reposting
		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(incoming_rate, 101)
		self.assertEqual(stock_value_difference, 808)

		return_dn.reload()
		self.assertEqual(return_dn.packed_items[0].incoming_rate, 101)

		# Cleanup data
		return_dn.cancel()
		dn.cancel()
		lcv.cancel()
		pr.cancel()

	def test_back_dated_entry_not_allowed(self):
		# Back dated stock transactions are only allowed to stock managers
		frappe.db.set_value(
			"Stock Settings", None, "role_allowed_to_create_edit_back_dated_transactions", "Stock Manager"
		)

		# Set User with Stock User role but not Stock Manager
		try:
			user = frappe.get_doc("User", "test@example.com")
			user.add_roles("Stock User")
			user.remove_roles("Stock Manager")

			frappe.set_user(user.name)

			stock_entry_on_today = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
			back_dated_se_1 = make_stock_entry(
				target="_Test Warehouse - _TC",
				qty=10,
				basic_rate=100,
				posting_date=add_days(today(), -1),
				do_not_submit=True,
			)

			# Block back-dated entry
			self.assertRaises(BackDatedStockTransaction, back_dated_se_1.submit)

			frappe.set_user("Administrator")
			user.add_roles("Stock Manager")
			frappe.set_user(user.name)

			# Back dated entry allowed to Stock Manager
			back_dated_se_2 = make_stock_entry(
				target="_Test Warehouse - _TC", qty=10, basic_rate=100, posting_date=add_days(today(), -1)
			)

			back_dated_se_2.cancel()
			stock_entry_on_today.cancel()

		finally:
			frappe.db.set_value(
				"Stock Settings", None, "role_allowed_to_create_edit_back_dated_transactions", None
			)
			frappe.set_user("Administrator")
			user.remove_roles("Stock Manager")

	def test_batchwise_item_valuation_moving_average(self):
		item, warehouses, batches = setup_item_valuation_test(valuation_method="Moving Average")

		# Incoming Entries for Stock Value check
		pr_entry_list = [
			(item, warehouses[0], batches[0], 1, 100),
			(item, warehouses[0], batches[1], 1, 50),
			(item, warehouses[0], batches[0], 1, 150),
			(item, warehouses[0], batches[1], 1, 100),
		]
		prs = create_purchase_receipt_entries_for_batchwise_item_valuation_test(pr_entry_list)
		sle_details = fetch_sle_details_for_doc_list(prs, ["stock_value"])
		sv_list = [d["stock_value"] for d in sle_details]
		expected_sv = [100, 150, 300, 400]
		self.assertEqual(expected_sv, sv_list, "Incorrect 'Stock Value' values")

		# Outgoing Entries for Stock Value Difference check
		dn_entry_list = [
			(item, warehouses[0], batches[1], 1, 200),
			(item, warehouses[0], batches[0], 1, 200),
			(item, warehouses[0], batches[1], 1, 200),
			(item, warehouses[0], batches[0], 1, 200),
		]
		dns = create_delivery_note_entries_for_batchwise_item_valuation_test(dn_entry_list)
		sle_details = fetch_sle_details_for_doc_list(dns, ["stock_value_difference"])
		svd_list = [-1 * d["stock_value_difference"] for d in sle_details]
		expected_incoming_rates = expected_abs_svd = [75, 125, 75, 125]

		self.assertEqual(expected_abs_svd, svd_list, "Incorrect 'Stock Value Difference' values")
		for dn, incoming_rate in zip(dns, expected_incoming_rates):
			self.assertEqual(
				dn.items[0].incoming_rate,
				incoming_rate,
				"Incorrect 'Incoming Rate' values fetched for DN items",
			)

	def test_batchwise_item_valuation_stock_reco(self):
		item, warehouses, batches = setup_item_valuation_test()
		state = {"stock_value": 0.0, "qty": 0.0}

		def update_invariants(exp_sles):
			for sle in exp_sles:
				state["stock_value"] += sle["stock_value_difference"]
				state["qty"] += sle["actual_qty"]
				sle["stock_value"] = state["stock_value"]
				sle["qty_after_transaction"] = state["qty"]

		osr1 = create_stock_reconciliation(
			warehouse=warehouses[0], item_code=item, qty=10, rate=100, batch_no=batches[1]
		)
		expected_sles = [
			{"actual_qty": 10, "stock_value_difference": 1000},
		]
		update_invariants(expected_sles)
		self.assertSLEs(osr1, expected_sles)

		osr2 = create_stock_reconciliation(
			warehouse=warehouses[0], item_code=item, qty=13, rate=200, batch_no=batches[0]
		)
		expected_sles = [
			{"actual_qty": 13, "stock_value_difference": 200 * 13},
		]
		update_invariants(expected_sles)
		self.assertSLEs(osr2, expected_sles)

		sr1 = create_stock_reconciliation(
			warehouse=warehouses[0], item_code=item, qty=5, rate=50, batch_no=batches[1]
		)

		expected_sles = [
			{"actual_qty": -10, "stock_value_difference": -10 * 100},
			{"actual_qty": 5, "stock_value_difference": 250},
		]
		update_invariants(expected_sles)
		self.assertSLEs(sr1, expected_sles)

		sr2 = create_stock_reconciliation(
			warehouse=warehouses[0], item_code=item, qty=20, rate=75, batch_no=batches[0]
		)
		expected_sles = [
			{"actual_qty": -13, "stock_value_difference": -13 * 200},
			{"actual_qty": 20, "stock_value_difference": 20 * 75},
		]
		update_invariants(expected_sles)
		self.assertSLEs(sr2, expected_sles)

	def test_batch_wise_valuation_across_warehouse(self):
		item_code, warehouses, batches = setup_item_valuation_test()
		source = warehouses[0]
		target = warehouses[1]

		unrelated_batch = make_stock_entry(
			item_code=item_code, target=source, batch_no=batches[1], qty=5, rate=10
		)
		self.assertSLEs(
			unrelated_batch,
			[
				{"actual_qty": 5, "stock_value_difference": 10 * 5},
			],
		)

		reciept = make_stock_entry(
			item_code=item_code, target=source, batch_no=batches[0], qty=5, rate=10
		)
		self.assertSLEs(
			reciept,
			[
				{"actual_qty": 5, "stock_value_difference": 10 * 5},
			],
		)

		transfer = make_stock_entry(
			item_code=item_code, source=source, target=target, batch_no=batches[0], qty=5
		)
		self.assertSLEs(
			transfer,
			[
				{"actual_qty": -5, "stock_value_difference": -10 * 5, "warehouse": source},
				{"actual_qty": 5, "stock_value_difference": 10 * 5, "warehouse": target},
			],
		)

		backdated_receipt = make_stock_entry(
			item_code=item_code,
			target=source,
			batch_no=batches[0],
			qty=5,
			rate=20,
			posting_date=add_days(today(), -1),
		)
		self.assertSLEs(
			backdated_receipt,
			[
				{"actual_qty": 5, "stock_value_difference": 20 * 5},
			],
		)

		# check reposted average rate in *future* transfer
		self.assertSLEs(
			transfer,
			[
				{
					"actual_qty": -5,
					"stock_value_difference": -15 * 5,
					"warehouse": source,
					"stock_value": 15 * 5 + 10 * 5,
				},
				{
					"actual_qty": 5,
					"stock_value_difference": 15 * 5,
					"warehouse": target,
					"stock_value": 15 * 5,
				},
			],
		)

		transfer_unrelated = make_stock_entry(
			item_code=item_code, source=source, target=target, batch_no=batches[1], qty=5
		)
		self.assertSLEs(
			transfer_unrelated,
			[
				{
					"actual_qty": -5,
					"stock_value_difference": -10 * 5,
					"warehouse": source,
					"stock_value": 15 * 5,
				},
				{
					"actual_qty": 5,
					"stock_value_difference": 10 * 5,
					"warehouse": target,
					"stock_value": 15 * 5 + 10 * 5,
				},
			],
		)

	def test_intermediate_average_batch_wise_valuation(self):
		"""A batch has moving average up until posting time,
		check if same is respected when backdated entry is inserted in middle"""
		item_code, warehouses, batches = setup_item_valuation_test()
		warehouse = warehouses[0]

		batch = batches[0]

		yesterday = make_stock_entry(
			item_code=item_code,
			target=warehouse,
			batch_no=batch,
			qty=1,
			rate=10,
			posting_date=add_days(today(), -1),
		)
		self.assertSLEs(
			yesterday,
			[
				{"actual_qty": 1, "stock_value_difference": 10},
			],
		)

		tomorrow = make_stock_entry(
			item_code=item_code,
			target=warehouse,
			batch_no=batches[0],
			qty=1,
			rate=30,
			posting_date=add_days(today(), 1),
		)
		self.assertSLEs(
			tomorrow,
			[
				{"actual_qty": 1, "stock_value_difference": 30},
			],
		)

		create_today = make_stock_entry(
			item_code=item_code, target=warehouse, batch_no=batches[0], qty=1, rate=20
		)
		self.assertSLEs(
			create_today,
			[
				{"actual_qty": 1, "stock_value_difference": 20},
			],
		)

		consume_today = make_stock_entry(
			item_code=item_code, source=warehouse, batch_no=batches[0], qty=1
		)
		self.assertSLEs(
			consume_today,
			[
				{"actual_qty": -1, "stock_value_difference": -15},
			],
		)

		consume_tomorrow = make_stock_entry(
			item_code=item_code,
			source=warehouse,
			batch_no=batches[0],
			qty=2,
			posting_date=add_days(today(), 2),
		)
		self.assertSLEs(
			consume_tomorrow,
			[
				{"stock_value_difference": -(30 + 15), "stock_value": 0, "qty_after_transaction": 0},
			],
		)

	def test_legacy_item_valuation_stock_entry(self):
		columns = [
			"stock_value_difference",
			"stock_value",
			"actual_qty",
			"qty_after_transaction",
			"stock_queue",
		]
		item, warehouses, batches = setup_item_valuation_test(use_batchwise_valuation=0)

		def check_sle_details_against_expected(sle_details, expected_sle_details, detail, columns):
			for i, (sle_vals, ex_sle_vals) in enumerate(zip(sle_details, expected_sle_details)):
				for col, sle_val, ex_sle_val in zip(columns, sle_vals, ex_sle_vals):
					if col == "stock_queue":
						sle_val = get_stock_value_from_q(sle_val)
						ex_sle_val = get_stock_value_from_q(ex_sle_val)
					self.assertEqual(
						sle_val, ex_sle_val, f"Incorrect {col} value on transaction #: {i} in {detail}"
					)

		# List used to defer assertions to prevent commits cause of error skipped rollback
		details_list = []

		# Test Material Receipt Entries
		se_entry_list_mr = [
			(item, None, warehouses[0], batches[0], 1, 50, "2021-01-21"),
			(item, None, warehouses[0], batches[1], 1, 100, "2021-01-23"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mr, "Material Receipt"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(50.0, 50.0, 1.0, 1.0, "[[1.0, 50.0]]"),
			(100.0, 150.0, 1.0, 2.0, "[[1.0, 50.0], [1.0, 100.0]]"),
		]
		details_list.append((sle_details, expected_sle_details, "Material Receipt Entries", columns))

		# Test Material Issue Entries
		se_entry_list_mi = [
			(item, warehouses[0], None, batches[1], 1, None, "2021-01-29"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mi, "Material Issue"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [(-50.0, 100.0, -1.0, 1.0, "[[1, 100.0]]")]
		details_list.append((sle_details, expected_sle_details, "Material Issue Entries", columns))

		# Run assertions
		for details in details_list:
			check_sle_details_against_expected(*details)

	def test_mixed_valuation_batches_fifo(self):
		item_code, warehouses, batches = setup_item_valuation_test(use_batchwise_valuation=0)
		warehouse = warehouses[0]

		state = {"qty": 0.0, "stock_value": 0.0}

		def update_invariants(exp_sles):
			for sle in exp_sles:
				state["stock_value"] += sle["stock_value_difference"]
				state["qty"] += sle["actual_qty"]
				sle["stock_value"] = state["stock_value"]
				sle["qty_after_transaction"] = state["qty"]
			return exp_sles

		old1 = make_stock_entry(
			item_code=item_code, target=warehouse, batch_no=batches[0], qty=10, rate=10
		)
		self.assertSLEs(
			old1,
			update_invariants(
				[
					{"actual_qty": 10, "stock_value_difference": 10 * 10, "stock_queue": [[10, 10]]},
				]
			),
		)
		old2 = make_stock_entry(
			item_code=item_code, target=warehouse, batch_no=batches[1], qty=10, rate=20
		)
		self.assertSLEs(
			old2,
			update_invariants(
				[
					{"actual_qty": 10, "stock_value_difference": 10 * 20, "stock_queue": [[10, 10], [10, 20]]},
				]
			),
		)
		old3 = make_stock_entry(
			item_code=item_code, target=warehouse, batch_no=batches[0], qty=5, rate=15
		)

		self.assertSLEs(
			old3,
			update_invariants(
				[
					{
						"actual_qty": 5,
						"stock_value_difference": 5 * 15,
						"stock_queue": [[10, 10], [10, 20], [5, 15]],
					},
				]
			),
		)

		new1 = make_stock_entry(item_code=item_code, target=warehouse, qty=10, rate=40)
		batches.append(new1.items[0].batch_no)
		# assert old queue remains
		self.assertSLEs(
			new1,
			update_invariants(
				[
					{
						"actual_qty": 10,
						"stock_value_difference": 10 * 40,
						"stock_queue": [[10, 10], [10, 20], [5, 15]],
					},
				]
			),
		)

		new2 = make_stock_entry(item_code=item_code, target=warehouse, qty=10, rate=42)
		batches.append(new2.items[0].batch_no)
		self.assertSLEs(
			new2,
			update_invariants(
				[
					{
						"actual_qty": 10,
						"stock_value_difference": 10 * 42,
						"stock_queue": [[10, 10], [10, 20], [5, 15]],
					},
				]
			),
		)

		# consume old batch as per FIFO
		consume_old1 = make_stock_entry(
			item_code=item_code, source=warehouse, qty=15, batch_no=batches[0]
		)
		self.assertSLEs(
			consume_old1,
			update_invariants(
				[
					{
						"actual_qty": -15,
						"stock_value_difference": -10 * 10 - 5 * 20,
						"stock_queue": [[5, 20], [5, 15]],
					},
				]
			),
		)

		# consume new batch as per batch
		consume_new2 = make_stock_entry(
			item_code=item_code, source=warehouse, qty=10, batch_no=batches[-1]
		)
		self.assertSLEs(
			consume_new2,
			update_invariants(
				[
					{"actual_qty": -10, "stock_value_difference": -10 * 42, "stock_queue": [[5, 20], [5, 15]]},
				]
			),
		)

		# finish all old batches
		consume_old2 = make_stock_entry(
			item_code=item_code, source=warehouse, qty=10, batch_no=batches[1]
		)
		self.assertSLEs(
			consume_old2,
			update_invariants(
				[
					{"actual_qty": -10, "stock_value_difference": -5 * 20 - 5 * 15, "stock_queue": []},
				]
			),
		)

		# finish all new batches
		consume_new1 = make_stock_entry(
			item_code=item_code, source=warehouse, qty=10, batch_no=batches[-2]
		)
		self.assertSLEs(
			consume_new1,
			update_invariants(
				[
					{"actual_qty": -10, "stock_value_difference": -10 * 40, "stock_queue": []},
				]
			),
		)

	def test_fifo_dependent_consumption(self):
		item = make_item("_TestFifoTransferRates")
		source = "_Test Warehouse - _TC"
		target = "Stores - _TC"

		rates = [10 * i for i in range(1, 20)]

		receipt = make_stock_entry(item_code=item.name, target=source, qty=10, do_not_save=True, rate=10)
		for rate in rates[1:]:
			row = frappe.copy_doc(receipt.items[0], ignore_no_copy=False)
			row.basic_rate = rate
			receipt.append("items", row)

		receipt.save()
		receipt.submit()

		expected_queues = []
		for idx, rate in enumerate(rates, start=1):
			expected_queues.append({"stock_queue": [[10, 10 * i] for i in range(1, idx + 1)]})
		self.assertSLEs(receipt, expected_queues)

		transfer = make_stock_entry(
			item_code=item.name, source=source, target=target, qty=10, do_not_save=True, rate=10
		)
		for rate in rates[1:]:
			row = frappe.copy_doc(transfer.items[0], ignore_no_copy=False)
			transfer.append("items", row)

		transfer.save()
		transfer.submit()

		# same exact queue should be transferred
		self.assertSLEs(transfer, expected_queues, sle_filters={"warehouse": target})

	def test_fifo_multi_item_repack_consumption(self):
		rm = make_item("_TestFifoRepackRM")
		packed = make_item("_TestFifoRepackFinished")
		warehouse = "_Test Warehouse - _TC"

		rates = [10 * i for i in range(1, 5)]

		receipt = make_stock_entry(
			item_code=rm.name, target=warehouse, qty=10, do_not_save=True, rate=10
		)
		for rate in rates[1:]:
			row = frappe.copy_doc(receipt.items[0], ignore_no_copy=False)
			row.basic_rate = rate
			receipt.append("items", row)

		receipt.save()
		receipt.submit()

		repack = make_stock_entry(
			item_code=rm.name, source=warehouse, qty=10, do_not_save=True, rate=10, purpose="Repack"
		)
		for rate in rates[1:]:
			row = frappe.copy_doc(repack.items[0], ignore_no_copy=False)
			repack.append("items", row)

		repack.append(
			"items",
			{
				"item_code": packed.name,
				"t_warehouse": warehouse,
				"qty": 1,
				"transfer_qty": 1,
			},
		)

		repack.save()
		repack.submit()

		# same exact queue should be transferred
		self.assertSLEs(
			repack, [{"incoming_rate": sum(rates) * 10}], sle_filters={"item_code": packed.name}
		)

	def test_negative_fifo_valuation(self):
		"""
		When stock goes negative discard FIFO queue.
		Only pervailing valuation rate should be used for making transactions in such cases.
		"""
		item = make_item(properties={"allow_negative_stock": 1}).name
		warehouse = "_Test Warehouse - _TC"

		receipt = make_stock_entry(item_code=item, target=warehouse, qty=10, rate=10)
		consume1 = make_stock_entry(item_code=item, source=warehouse, qty=15)

		self.assertSLEs(consume1, [{"stock_value": -5 * 10, "stock_queue": [[-5, 10]]}])

		consume2 = make_stock_entry(item_code=item, source=warehouse, qty=5)
		self.assertSLEs(consume2, [{"stock_value": -10 * 10, "stock_queue": [[-10, 10]]}])

		receipt2 = make_stock_entry(item_code=item, target=warehouse, qty=15, rate=15)
		self.assertSLEs(receipt2, [{"stock_queue": [[5, 15]], "stock_value_difference": 175}])

	def test_dependent_gl_entry_reposting(self):
		def _get_stock_credit(doc):
			return frappe.db.get_value(
				"GL Entry",
				{
					"voucher_no": doc.name,
					"voucher_type": doc.doctype,
					"is_cancelled": 0,
					"account": "Stock In Hand - TCP1",
				},
				"sum(credit)",
			)

		def _day(days):
			return add_to_date(date=today(), days=days)

		item = make_item().name
		A = "Stores - TCP1"
		B = "Work In Progress - TCP1"
		C = "Finished Goods - TCP1"

		make_stock_entry(item_code=item, to_warehouse=A, qty=5, rate=10, posting_date=_day(0))
		make_stock_entry(item_code=item, from_warehouse=A, to_warehouse=B, qty=5, posting_date=_day(1))
		depdendent_consumption = make_stock_entry(
			item_code=item, from_warehouse=B, qty=5, posting_date=_day(2)
		)
		self.assertEqual(50, _get_stock_credit(depdendent_consumption))

		# backdated receipt - should trigger GL repost of all previous stock entries
		bd_receipt = make_stock_entry(
			item_code=item, to_warehouse=A, qty=5, rate=20, posting_date=_day(-1)
		)
		self.assertEqual(100, _get_stock_credit(depdendent_consumption))

		# cancelling receipt should reset it back
		bd_receipt.cancel()
		self.assertEqual(50, _get_stock_credit(depdendent_consumption))

		bd_receipt2 = make_stock_entry(
			item_code=item, to_warehouse=A, qty=2, rate=20, posting_date=_day(-2)
		)
		# total as per FIFO -> 2 * 20 + 3 * 10 = 70
		self.assertEqual(70, _get_stock_credit(depdendent_consumption))

		# transfer WIP material to final destination and consume it all
		depdendent_consumption.cancel()
		make_stock_entry(item_code=item, from_warehouse=B, to_warehouse=C, qty=5, posting_date=_day(3))
		final_consumption = make_stock_entry(
			item_code=item, from_warehouse=C, qty=5, posting_date=_day(4)
		)
		# exact amount gets consumed
		self.assertEqual(70, _get_stock_credit(final_consumption))

		# cancel original backdated receipt - should repost A -> B -> C
		bd_receipt2.cancel()
		# original amount
		self.assertEqual(50, _get_stock_credit(final_consumption))

	def test_tie_breaking(self):
		frappe.flags.dont_execute_stock_reposts = True
		self.addCleanup(frappe.flags.pop, "dont_execute_stock_reposts")

		item = make_item().name
		warehouse = "_Test Warehouse - _TC"

		posting_date = "2022-01-01"
		posting_time = "00:00:01"
		sle = frappe.qb.DocType("Stock Ledger Entry")

		def ordered_qty_after_transaction():
			return (
				frappe.qb.from_(sle)
				.select("qty_after_transaction")
				.where((sle.item_code == item) & (sle.warehouse == warehouse) & (sle.is_cancelled == 0))
				.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
				.orderby(sle.creation)
			).run(pluck=True)

		first = make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=10,
			posting_time=posting_time,
			posting_date=posting_date,
			do_not_submit=True,
		)
		second = make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=1,
			posting_date=posting_date,
			posting_time=posting_time,
			do_not_submit=True,
		)

		first.submit()
		second.submit()

		self.assertEqual([10, 11], ordered_qty_after_transaction())

		first.cancel()
		self.assertEqual([1], ordered_qty_after_transaction())

		backdated = make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=1,
			posting_date="2021-01-01",
			posting_time=posting_time,
		)
		self.assertEqual([1, 2], ordered_qty_after_transaction())

		backdated.cancel()
		self.assertEqual([1], ordered_qty_after_transaction())

	def test_timestamp_clash(self):

		item = make_item().name
		warehouse = "_Test Warehouse - _TC"

		reciept = make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=100,
			rate=10,
			posting_date="2021-01-01",
			posting_time="01:00:00",
		)

		consumption = make_stock_entry(
			item_code=item,
			from_warehouse=warehouse,
			qty=50,
			posting_date="2021-01-01",
			posting_time="02:00:00.1234",  # ms are possible when submitted without editing posting time
		)

		backdated_receipt = make_stock_entry(
			item_code=item,
			to_warehouse=warehouse,
			qty=100,
			posting_date="2021-01-01",
			rate=10,
			posting_time="02:00:00",  # same posting time as consumption but ms part stripped
		)

		try:
			backdated_receipt.cancel()
		except Exception as e:
			self.fail("Double processing of qty for clashing timestamp.")

	@change_settings("System Settings", {"float_precision": 3, "currency_precision": 2})
	def test_transfer_invariants(self):
		"""Extact stock value should be transferred."""

		item = make_item(
			properties={
				"valuation_method": "Moving Average",
				"stock_uom": "Kg",
			}
		).name
		source_warehouse = "Stores - TCP1"
		target_warehouse = "Finished Goods - TCP1"

		make_purchase_receipt(
			item=item,
			warehouse=source_warehouse,
			qty=20,
			conversion_factor=1000,
			uom="Tonne",
			rate=156_526.0,
			company="_Test Company with perpetual inventory",
		)
		transfer = make_stock_entry(
			item=item, from_warehouse=source_warehouse, to_warehouse=target_warehouse, qty=1_728.0
		)

		filters = {"voucher_no": transfer.name, "voucher_type": transfer.doctype, "is_cancelled": 0}
		sles = frappe.get_all(
			"Stock Ledger Entry",
			fields=["*"],
			filters=filters,
			order_by="timestamp(posting_date, posting_time), creation",
		)
		self.assertEqual(abs(sles[0].stock_value_difference), sles[1].stock_value_difference)

	@change_settings("System Settings", {"float_precision": 4})
	def test_negative_qty_with_precision(self):
		"Test if system precision is respected while validating negative qty."
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.utils import get_stock_balance

		item_code = "ItemPrecisionTest"
		warehouse = "_Test Warehouse - _TC"
		create_item(item_code, is_stock_item=1, stock_uom="Kg")

		create_stock_reconciliation(item_code=item_code, warehouse=warehouse, qty=559.8327, rate=100)

		make_stock_entry(item_code=item_code, source=warehouse, qty=470.84, rate=100)
		self.assertEqual(get_stock_balance(item_code, warehouse), 88.9927)

		settings = frappe.get_doc("System Settings")
		settings.float_precision = 3
		settings.save()

		# To deliver 100 qty we fall short of 11.0073 qty (11.007 with precision 3)
		# Stock up with 11.007 (balance in db becomes 99.9997, on UI it will show as 100)
		make_stock_entry(item_code=item_code, target=warehouse, qty=11.007, rate=100)
		self.assertEqual(get_stock_balance(item_code, warehouse), 99.9997)

		# See if delivery note goes through
		# Negative qty error should not be raised as 99.9997 is 100 with precision 3 (system precision)
		dn = create_delivery_note(
			item_code=item_code,
			qty=100,
			rate=150,
			warehouse=warehouse,
			company="_Test Company",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			do_not_submit=True,
		)
		dn.submit()

		self.assertEqual(flt(get_stock_balance(item_code, warehouse), 3), 0.000)

	@change_settings("System Settings", {"float_precision": 4})
	def test_future_negative_qty_with_precision(self):
		"""
		Ledger:
		| Voucher | Qty		| Balance
		-------------------
		| Reco	  | 559.8327| 559.8327
		| SE	  | -470.84	| [Backdated] (new bal: 88.9927)
		| SE	  | 11.007	| 570.8397 (new bal: 99.9997)
		| DN	  | -100	| 470.8397 (new bal: -0.0003)

		Check if future negative qty is asserted as per precision 3.
		-0.0003 should be considered as 0.000
		"""
		from erpnext.stock.doctype.item.test_item import create_item

		item_code = "ItemPrecisionTest"
		warehouse = "_Test Warehouse - _TC"
		create_item(item_code, is_stock_item=1, stock_uom="Kg")

		create_stock_reconciliation(
			item_code=item_code,
			warehouse=warehouse,
			qty=559.8327,
			rate=100,
			posting_date=add_days(today(), -2),
		)
		make_stock_entry(item_code=item_code, target=warehouse, qty=11.007, rate=100)
		create_delivery_note(
			item_code=item_code,
			qty=100,
			rate=150,
			warehouse=warehouse,
			company="_Test Company",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
		)

		settings = frappe.get_doc("System Settings")
		settings.float_precision = 3
		settings.save()

		# Make backdated SE and make sure SE goes through as per precision (no negative qty error)
		make_stock_entry(
			item_code=item_code, source=warehouse, qty=470.84, rate=100, posting_date=add_days(today(), -1)
		)


def create_repack_entry(**args):
	args = frappe._dict(args)
	repack = frappe.new_doc("Stock Entry")
	repack.stock_entry_type = "Repack"
	repack.company = args.company or "_Test Company"
	repack.posting_date = args.posting_date
	repack.set_posting_time = 1
	repack.append(
		"items",
		{
			"item_code": "_Test Item for Reposting",
			"s_warehouse": "Stores - _TC",
			"qty": 5,
			"conversion_factor": 1,
			"expense_account": "Stock Adjustment - _TC",
			"cost_center": "Main - _TC",
		},
	)

	repack.append(
		"items",
		{
			"item_code": "_Test Finished Item for Reposting",
			"t_warehouse": "Finished Goods - _TC",
			"qty": 1,
			"conversion_factor": 1,
			"expense_account": "Stock Adjustment - _TC",
			"cost_center": "Main - _TC",
		},
	)

	repack.append(
		"additional_costs",
		{
			"expense_account": "Freight and Forwarding Charges - _TC",
			"description": "transport cost",
			"amount": 40,
		},
	)

	repack.save()
	repack.submit()

	return repack


def create_product_bundle_item(new_item_code, packed_items):
	if not frappe.db.exists("Product Bundle", new_item_code):
		item = frappe.new_doc("Product Bundle")
		item.new_item_code = new_item_code

		for d in packed_items:
			item.append("items", {"item_code": d[0], "qty": d[1]})

		item.save()


def create_items(items=None, uoms=None):
	if not items:
		items = [
			"_Test Item for Reposting",
			"_Test Finished Item for Reposting",
			"_Test Subcontracted Item for Reposting",
			"_Test Bundled Item for Reposting",
		]

	for d in items:
		properties = {"valuation_method": "FIFO"}
		if d == "_Test Bundled Item for Reposting":
			properties.update({"is_stock_item": 0})
		elif d == "_Test Subcontracted Item for Reposting":
			properties.update({"is_sub_contracted_item": 1})

		make_item(d, properties=properties, uoms=uoms)

	return items


def setup_item_valuation_test(
	valuation_method="FIFO", suffix=None, use_batchwise_valuation=1, batches_list=["X", "Y"]
):
	from erpnext.stock.doctype.batch.batch import make_batch
	from erpnext.stock.doctype.item.test_item import make_item
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	if not suffix:
		suffix = get_unique_suffix()

	item = make_item(
		f"IV - Test Item {valuation_method} {suffix}",
		dict(valuation_method=valuation_method, has_batch_no=1, create_new_batch=1),
	)
	warehouses = [create_warehouse(f"IV - Test Warehouse {i}") for i in ["J", "K"]]
	batches = [f"IV - Test Batch {i} {valuation_method} {suffix}" for i in batches_list]

	for i, batch_id in enumerate(batches):
		if not frappe.db.exists("Batch", batch_id):
			ubw = use_batchwise_valuation
			if isinstance(use_batchwise_valuation, (list, tuple)):
				ubw = use_batchwise_valuation[i]
			batch = frappe.get_doc(
				frappe._dict(
					doctype="Batch", batch_id=batch_id, item=item.item_code, use_batchwise_valuation=ubw
				)
			).insert()
			batch.use_batchwise_valuation = ubw
			batch.db_update()

	return item.item_code, warehouses, batches


def create_purchase_receipt_entries_for_batchwise_item_valuation_test(pr_entry_list):
	from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

	prs = []

	for item, warehouse, batch_no, qty, rate in pr_entry_list:
		pr = make_purchase_receipt(item=item, warehouse=warehouse, qty=qty, rate=rate, batch_no=batch_no)
		prs.append(pr)

	return prs


def create_delivery_note_entries_for_batchwise_item_valuation_test(dn_entry_list):
	from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
	from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

	dns = []
	for item, warehouse, batch_no, qty, rate in dn_entry_list:
		so = make_sales_order(
			rate=rate, qty=qty, item=item, warehouse=warehouse, against_blanket_order=0
		)

		dn = make_delivery_note(so.name)
		dn.items[0].batch_no = batch_no
		dn.insert()
		dn.submit()
		dns.append(dn)
	return dns


def fetch_sle_details_for_doc_list(doc_list, columns, as_dict=1):
	return frappe.db.sql(
		f"""
		SELECT { ', '.join(columns)}
		FROM `tabStock Ledger Entry`
		WHERE
			voucher_no IN %(voucher_nos)s
			and docstatus = 1
		ORDER BY timestamp(posting_date, posting_time) ASC, CREATION ASC
	""",
		dict(voucher_nos=[doc.name for doc in doc_list]),
		as_dict=as_dict,
	)


def get_stock_value_from_q(q):
	return sum(r * q for r, q in json.loads(q))


def create_stock_entry_entries_for_batchwise_item_valuation_test(se_entry_list, purpose):
	ses = []
	for item, source, target, batch, qty, rate, posting_date in se_entry_list:
		args = dict(
			item_code=item,
			qty=qty,
			company="_Test Company",
			batch_no=batch,
			posting_date=posting_date,
			purpose=purpose,
		)

		if purpose == "Material Receipt":
			args.update(dict(to_warehouse=target, rate=rate))

		elif purpose == "Material Issue":
			args.update(dict(from_warehouse=source))

		elif purpose == "Material Transfer":
			args.update(dict(from_warehouse=source, to_warehouse=target))

		else:
			raise ValueError(f"Invalid purpose: {purpose}")
		ses.append(make_stock_entry(**args))

	return ses


def get_unique_suffix():
	# Used to isolate valuation sensitive
	# tests to prevent future tests from failing.
	return str(uuid4())[:8].upper()


class TestDeferredNaming(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		cls.gle_autoname = frappe.get_meta("GL Entry").autoname
		cls.sle_autoname = frappe.get_meta("Stock Ledger Entry").autoname

	def setUp(self) -> None:
		self.item = make_item().name
		self.warehouse = "Stores - TCP1"
		self.company = "_Test Company with perpetual inventory"

	def tearDown(self) -> None:
		make_property_setter(
			doctype="GL Entry",
			for_doctype=True,
			property="autoname",
			value=self.gle_autoname,
			property_type="Data",
			fieldname=None,
		)
		make_property_setter(
			doctype="Stock Ledger Entry",
			for_doctype=True,
			property="autoname",
			value=self.sle_autoname,
			property_type="Data",
			fieldname=None,
		)

		# since deferred naming autocommits, commit all changes to avoid flake
		frappe.db.commit()  # nosemgrep

	@staticmethod
	def get_gle_sles(se):
		filters = {"voucher_type": se.doctype, "voucher_no": se.name}
		gle = set(frappe.get_list("GL Entry", filters, pluck="name"))
		sle = set(frappe.get_list("Stock Ledger Entry", filters, pluck="name"))
		return gle, sle

	def test_deferred_naming(self):
		se = make_stock_entry(
			item_code=self.item, to_warehouse=self.warehouse, qty=10, rate=100, company=self.company
		)

		gle, sle = self.get_gle_sles(se)
		rename_gle_sle_docs()
		renamed_gle, renamed_sle = self.get_gle_sles(se)

		self.assertFalse(gle & renamed_gle, msg="GLEs not renamed")
		self.assertFalse(sle & renamed_sle, msg="SLEs not renamed")
		se.cancel()

	def test_hash_naming(self):
		# disable naming series
		for doctype in ("GL Entry", "Stock Ledger Entry"):
			make_property_setter(
				doctype=doctype,
				for_doctype=True,
				property="autoname",
				value="hash",
				property_type="Data",
				fieldname=None,
			)

		se = make_stock_entry(
			item_code=self.item, to_warehouse=self.warehouse, qty=10, rate=100, company=self.company
		)

		gle, sle = self.get_gle_sles(se)
		rename_gle_sle_docs()
		renamed_gle, renamed_sle = self.get_gle_sles(se)

		self.assertEqual(gle, renamed_gle, msg="GLEs are renamed while using hash naming")
		self.assertEqual(sle, renamed_sle, msg="SLEs are renamed while using hash naming")
		se.cancel()
