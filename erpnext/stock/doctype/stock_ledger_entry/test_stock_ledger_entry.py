# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import json
from operator import itemgetter
from uuid import uuid4

import frappe
from frappe.core.page.permission_manager.permission_manager import reset
from frappe.utils import add_days, today

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
from erpnext.tests.utils import ERPNextTestCase


class TestStockLedgerEntry(ERPNextTestCase):
	def setUp(self):
		items = create_items()
		reset('Stock Entry')

		# delete SLE and BINs for all items
		frappe.db.sql("delete from `tabStock Ledger Entry` where item_code in (%s)" % (', '.join(['%s']*len(items))), items)
		frappe.db.sql("delete from `tabBin` where item_code in (%s)" % (', '.join(['%s']*len(items))), items)

	def test_item_cost_reposting(self):
		company = "_Test Company"

		# _Test Item for Reposting at Stores warehouse on 10-04-2020: Qty = 50, Rate = 100
		create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - _TC",
			qty=50,
			rate=100,
			company=company,
			expense_account = "Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-10',
			posting_time='14:00'
		)

		# _Test Item for Reposting at FG warehouse on 20-04-2020: Qty = 10, Rate = 200
		create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Finished Goods - _TC",
			qty=10,
			rate=200,
			company=company,
			expense_account="Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-20',
			posting_time='14:00'
		)

		# _Test Item for Reposting transferred from Stores to FG warehouse on 30-04-2020
		se = make_stock_entry(
			item_code="_Test Item for Reposting",
			source="Stores - _TC",
			target="Finished Goods - _TC",
			company=company,
			qty=10,
			expense_account="Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-30',
			posting_time='14:00'
		)
		target_wh_sle = frappe.db.get_value('Stock Ledger Entry', {
			"item_code": "_Test Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"voucher_type": "Stock Entry",
			"voucher_no": se.name
		}, ["valuation_rate"], as_dict=1)

		self.assertEqual(target_wh_sle.get("valuation_rate"), 150)

		# Repack entry on 5-5-2020
		repack = create_repack_entry(company=company, posting_date='2020-05-05', posting_time='14:00')

		finished_item_sle = frappe.db.get_value('Stock Ledger Entry', {
			"item_code": "_Test Finished Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"voucher_type": "Stock Entry",
			"voucher_no": repack.name
		}, ["incoming_rate", "valuation_rate"], as_dict=1)
		self.assertEqual(finished_item_sle.get("incoming_rate"), 540)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 540)

		# Reconciliation for _Test Item for Reposting at Stores on 12-04-2020: Qty = 50, Rate = 150
		sr = create_stock_reconciliation(
			item_code="_Test Item for Reposting",
			warehouse="Stores - _TC",
			qty=50,
			rate=150,
			company=company,
			expense_account ="Stock Adjustment - _TC" if frappe.get_all("Stock Ledger Entry") else "Temporary Opening - _TC",
			posting_date='2020-04-12',
			posting_time='14:00'
		)


		# Check valuation rate of finished goods warehouse after back-dated entry at Stores
		target_wh_sle = get_previous_sle({
			"item_code": "_Test Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"posting_date": '2020-04-30',
			"posting_time": '14:00'
		})
		self.assertEqual(target_wh_sle.get("incoming_rate"), 150)
		self.assertEqual(target_wh_sle.get("valuation_rate"), 175)

		# Check valuation rate of repacked item after back-dated entry at Stores
		finished_item_sle = frappe.db.get_value('Stock Ledger Entry', {
			"item_code": "_Test Finished Item for Reposting",
			"warehouse": "Finished Goods - _TC",
			"voucher_type": "Stock Entry",
			"voucher_no": repack.name
		}, ["incoming_rate", "valuation_rate"], as_dict=1)
		self.assertEqual(finished_item_sle.get("incoming_rate"), 790)
		self.assertEqual(finished_item_sle.get("valuation_rate"), 790)

		# Check updated rate in Repack entry
		repack.reload()
		self.assertEqual(repack.items[0].get("basic_rate"), 150)
		self.assertEqual(repack.items[1].get("basic_rate"), 750)

	def test_purchase_return_valuation_reposting(self):
		pr = make_purchase_receipt(company="_Test Company", posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code="_Test Item for Reposting", qty=5, rate=100)

		return_pr = make_purchase_receipt(company="_Test Company", posting_date='2020-04-15',
			warehouse="Stores - _TC", item_code="_Test Item for Reposting", is_return=1, return_against=pr.name, qty=-2)

		# check sle
		outgoing_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, ["outgoing_rate", "stock_value_difference"])

		self.assertEqual(outgoing_rate, 100)
		self.assertEqual(stock_value_difference, -200)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		outgoing_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, ["outgoing_rate", "stock_value_difference"])

		self.assertEqual(outgoing_rate, 110)
		self.assertEqual(stock_value_difference, -220)

	def test_sales_return_valuation_reposting(self):
		company = "_Test Company"
		item_code="_Test Item for Reposting"

		# Purchase Return: Qty = 5, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code=item_code, qty=5, rate=100)

		#Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(item_code=item_code, qty=5, rate=150, warehouse="Stores - _TC",
			company=company, expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

		# check outgoing_rate for DN
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 5)

		self.assertEqual(dn.items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(is_return=1, return_against=dn.name, item_code=item_code, qty=-2, rate=150,
			company=company, warehouse="Stores - _TC", expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

		# check incoming rate for Return entry
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(return_dn.items[0].incoming_rate, 100)
		self.assertEqual(incoming_rate, 100)
		self.assertEqual(stock_value_difference, 200)

		#-------------------------------

		# Landed Cost Voucher to update the rate of incoming Purchase Return: Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# check outgoing_rate for DN after reposting
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 5)
		self.assertEqual(outgoing_rate, 110)

		dn.reload()
		self.assertEqual(dn.items[0].incoming_rate, 110)

		# check incoming rate for Return entry after reposting
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

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
		packed_item_code="_Test Item for Reposting"
		bundled_item = "_Test Bundled Item for Reposting"
		create_product_bundle_item(bundled_item, [[packed_item_code, 4]])

		# Purchase Return: Qty = 50, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code=packed_item_code, qty=50, rate=100)

		#Delivery Note: Qty = 5, Rate = 150
		dn = create_delivery_note(item_code=bundled_item, qty=5, rate=150, warehouse="Stores - _TC",
			company=company, expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

		# check outgoing_rate for DN
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 20)

		self.assertEqual(dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(outgoing_rate, 100)

		# Return Entry: Qty = -2, Rate = 150
		return_dn = create_delivery_note(is_return=1, return_against=dn.name, item_code=bundled_item, qty=-2, rate=150,
			company=company, warehouse="Stores - _TC", expense_account="Cost of Goods Sold - _TC", cost_center="Main - _TC")

		# check incoming rate for Return entry
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(return_dn.packed_items[0].incoming_rate, 100)
		self.assertEqual(incoming_rate, 100)
		self.assertEqual(stock_value_difference, 800)

		#-------------------------------

		# Landed Cost Voucher to update the rate of incoming Purchase Return: Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		# check outgoing_rate for DN after reposting
		outgoing_rate = abs(frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 20)
		self.assertEqual(outgoing_rate, 101)

		dn.reload()
		self.assertEqual(dn.packed_items[0].incoming_rate, 101)

		# check incoming rate for Return entry after reposting
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": return_dn.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEqual(incoming_rate, 101)
		self.assertEqual(stock_value_difference, 808)

		return_dn.reload()
		self.assertEqual(return_dn.packed_items[0].incoming_rate, 101)

		# Cleanup data
		return_dn.cancel()
		dn.cancel()
		lcv.cancel()
		pr.cancel()

	def test_sub_contracted_item_costing(self):
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

		company = "_Test Company"
		rm_item_code="_Test Item for Reposting"
		subcontracted_item = "_Test Subcontracted Item for Reposting"

		frappe.db.set_value("Buying Settings", None, "backflush_raw_materials_of_subcontract_based_on", "BOM")
		make_bom(item = subcontracted_item, raw_materials =[rm_item_code], currency="INR")

		# Purchase raw materials on supplier warehouse: Qty = 50, Rate = 100
		pr = make_purchase_receipt(company=company, posting_date='2020-04-10',
			warehouse="Stores - _TC", item_code=rm_item_code, qty=10, rate=100)

		# Purchase Receipt for subcontracted item
		pr1 = make_purchase_receipt(company=company, posting_date='2020-04-20',
			warehouse="Finished Goods - _TC", supplier_warehouse="Stores - _TC",
			item_code=subcontracted_item, qty=10, rate=20, is_subcontracted="Yes")

		self.assertEqual(pr1.items[0].valuation_rate, 120)

		# Update raw material's valuation via LCV, Additional cost = 50
		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		pr1.reload()
		self.assertEqual(pr1.items[0].valuation_rate, 125)

		# check outgoing_rate for DN after reposting
		incoming_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": pr1.name, "item_code": subcontracted_item}, "incoming_rate")
		self.assertEqual(incoming_rate, 125)

		# cleanup data
		pr1.cancel()
		lcv.cancel()
		pr.cancel()

	def test_back_dated_entry_not_allowed(self):
		# Back dated stock transactions are only allowed to stock managers
		frappe.db.set_value("Stock Settings", None,
			"role_allowed_to_create_edit_back_dated_transactions", "Stock Manager")

		# Set User with Stock User role but not Stock Manager
		try:
			user = frappe.get_doc("User", "test@example.com")
			user.add_roles("Stock User")
			user.remove_roles("Stock Manager")

			frappe.set_user(user.name)

			stock_entry_on_today = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
			back_dated_se_1 = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100,
				posting_date=add_days(today(), -1), do_not_submit=True)

			# Block back-dated entry
			self.assertRaises(BackDatedStockTransaction, back_dated_se_1.submit)

			frappe.set_user("Administrator")
			user.add_roles("Stock Manager")
			frappe.set_user(user.name)

			# Back dated entry allowed to Stock Manager
			back_dated_se_2 = make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100,
				posting_date=add_days(today(), -1))

			back_dated_se_2.cancel()
			stock_entry_on_today.cancel()

		finally:
			frappe.db.set_value("Stock Settings", None, "role_allowed_to_create_edit_back_dated_transactions", None)
			frappe.set_user("Administrator")
			user.remove_roles("Stock Manager")

	def test_batchwise_item_valuation_fifo(self):
		suffix = get_unique_suffix()
		item, warehouses, batches = setup_item_valuation_test(
			valuation_method="FIFO", suffix=suffix
		)

		# Incoming Entries for Stock Value check
		pr_entry_list = [
			(item, warehouses[0], batches[0], 1, 100),
			(item, warehouses[1], batches[0], 1,  25),
			(item, warehouses[0], batches[1], 1,  50),
			(item, warehouses[0], batches[0], 1, 150),
		]
		prs = create_purchase_receipt_entries_for_batchwise_item_valuation_test(pr_entry_list)
		sle_details = fetch_sle_details_for_doc_list(prs, ['stock_value'])
		sv_list = [d['stock_value'] for d in sle_details]
		expected_sv = [100, 25, 50, 250]
		abs_sv_diff = [abs(x - y) for x, y in zip(expected_sv, sv_list)]

		# Outgoing Entries for Stock Value Difference check
		dn_entry_list = [
			(item, warehouses[0], batches[1], 1, 200),
			(item, warehouses[0], batches[0], 1, 200),
			(item, warehouses[1], batches[0], 1, 200),
			(item, warehouses[0], batches[0], 1, 200)
		]
		dns = create_delivery_note_entries_for_batchwise_item_valuation_test(dn_entry_list)
		sle_details = fetch_sle_details_for_doc_list(dns, ['stock_value_difference'])
		svd_list = [d['stock_value_difference'] for d in sle_details]
		expected_incoming_rates = expected_abs_svd = [50, 100, 25, 150]
		abs_svd_diff = [abs(x + y) for x, y in zip(expected_abs_svd, svd_list)]

		self.assertTrue(sum(abs_sv_diff) == 0, "Incorrect 'Stock Value' values")
		self.assertTrue(sum(abs_svd_diff) == 0, "Incorrect 'Stock Value Difference' values")
		for dn, incoming_rate in zip(dns, expected_incoming_rates):
			self.assertEqual(
				dn.items[0].incoming_rate, incoming_rate,
				"Incorrect 'Incoming Rate' values fetched for DN items"
			)

	def test_batchwise_item_valuation_moving_average(self):
		suffix = get_unique_suffix()
		item, warehouses, batches = setup_item_valuation_test(
			valuation_method="Moving Average", suffix=suffix
		)

		# Incoming Entries for Stock Value check
		pr_entry_list = [
			(item, warehouses[0], batches[0], 1, 100),
			(item, warehouses[0], batches[1], 1,  50),
			(item, warehouses[0], batches[0], 1, 150),
			(item, warehouses[0], batches[1], 1, 100),
		]
		prs = create_purchase_receipt_entries_for_batchwise_item_valuation_test(pr_entry_list)
		sle_details = fetch_sle_details_for_doc_list(prs, ['stock_value'])
		sv_list = [d['stock_value'] for d in sle_details]
		expected_sv = [100, 50, 250, 150]
		abs_sv_diff = [abs(x - y) for x, y in zip(expected_sv, sv_list)]

		# Outgoing Entries for Stock Value Difference check
		dn_entry_list = [
			(item, warehouses[0], batches[1], 1, 200),
			(item, warehouses[0], batches[0], 1, 200),
			(item, warehouses[0], batches[1], 1, 200),
			(item, warehouses[0], batches[0], 1, 200)
		]
		dns = create_delivery_note_entries_for_batchwise_item_valuation_test(dn_entry_list)
		sle_details = fetch_sle_details_for_doc_list(dns, ['stock_value_difference'])
		svd_list = [d['stock_value_difference'] for d in sle_details]
		expected_incoming_rates = expected_abs_svd = [75, 125, 75, 125]
		abs_svd_diff = [abs(x + y) for x, y in zip(expected_abs_svd, svd_list)]

		self.assertTrue(sum(abs_sv_diff) == 0, "Incorrect 'Stock Value' values")
		self.assertTrue(sum(abs_svd_diff) == 0, "Incorrect 'Stock Value Difference' values")
		for dn, incoming_rate in zip(dns, expected_incoming_rates):
			self.assertEqual(
				dn.items[0].incoming_rate, incoming_rate,
				"Incorrect 'Incoming Rate' values fetched for DN items"
			)


	def test_batchwise_item_valuation_stock_reco(self):
		suffix = get_unique_suffix()
		item, warehouses, batches = setup_item_valuation_test(
			valuation_method="FIFO", suffix=suffix
		)

		# Check Opening Stock Entries
		sr_entry_list_os = [
			(item, warehouses[0], batches[1], 10, 100),
			(item, warehouses[0], batches[0], 13, 200),
		]
		srs = create_stock_reco_entries_for_batchwise_item_valuation_test(
			sr_entry_list_os, purpose="Opening Stock"
		)
		sle_details = fetch_sle_details_for_doc_list(srs, [
			'stock_value_difference',
			'stock_value',
			'stock_queue',
			'actual_qty',
			'qty_after_transaction'
		], as_dict=0)
		for (svd, sv, sq, aq, qat), (*_, qty, rate) in zip(sle_details, sr_entry_list_os):
			expected_sv = rate * qty
			sv_from_q = get_stock_value_from_q(sq)
			self.assertTrue((qty == aq) and (aq == qat))
			self.assertTrue((expected_sv == svd) and (svd == sv))
			self.assertEqual(expected_sv, sv_from_q)

		# Check Stock Reconciliation entries
		sr_entry_list_sr = [
			(item, warehouses[0], batches[1], 5, 50),
			(item, warehouses[0], batches[0], 20, 75)
		]
		srs = create_stock_reco_entries_for_batchwise_item_valuation_test(
			sr_entry_list_sr, purpose="Stock Reconciliation"
		)
		sle_details = fetch_sle_details_for_doc_list(srs, [
			'stock_value_difference',
			'stock_value',
			'stock_queue',
			'actual_qty',
			'qty_after_transaction'
		], as_dict=0)

		expected_details = [
			(*([sr_entry_list_sr[0][-1] * sr_entry_list_sr[0][-2]]*3), *([sr_entry_list_sr[0][-2]]*2)),
			(-sr_entry_list_os[0][-1] * sr_entry_list_os[0][-2], 0, 0, -sr_entry_list_os[0][-2], 0),
			(*([sr_entry_list_sr[1][-1] * sr_entry_list_sr[1][-2]]*3), *([sr_entry_list_sr[1][-2]]*2)),
			(-sr_entry_list_os[1][-1] * sr_entry_list_os[1][-2], 0, 0, -sr_entry_list_os[1][-2], 0)
		]

		sle_details = [
			*sorted(sle_details[:2], key=lambda sd: -sd[0]),
			*sorted(sle_details[2:], key=lambda sd: -sd[0])
		]
		for sd, ed in zip(sle_details, expected_details):
			svd, sv, sq, aq, qat = sd
			ex_svd, ex_sv, ex_sqv, ex_aq, ex_qat = ed
			self.assertEqual(svd, ex_svd)
			self.assertEqual(sv, ex_sv)
			self.assertEqual(get_stock_value_from_q(sq), ex_sqv)
			self.assertEqual(aq, ex_aq)
			self.assertEqual(qat, ex_qat)


	def test_batchwise_item_valuation_stock_entry(self):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost_sl_entries
		suffix = get_unique_suffix()
		item, warehouses, batches = setup_item_valuation_test(
			valuation_method="FIFO", suffix=suffix
		)

		columns = [
				'stock_value_difference',
				'stock_value',
				'actual_qty',
				'qty_after_transaction',
				'stock_queue',
		]

		def check_sle_details_against_expected(sle_details, expected_sle_details, detail, columns):
			for i, (sle_vals, ex_sle_vals) in enumerate(zip(sle_details, expected_sle_details)):
				for col, sle_val, ex_sle_val in zip(columns, sle_vals, ex_sle_vals):
					if col == 'stock_queue':
						sle_val = get_stock_value_from_q(sle_val)
						ex_sle_val = get_stock_value_from_q(ex_sle_val)
					self.assertEqual(
						sle_val, ex_sle_val,
						f"Incorrect {col} value on transaction #: {i} in {detail}"
					)

		# List used to defer assertions to prevent commits cause of error skipped rollback
		details_list = []


		# Test Material Receipt Entries
		se_entry_list_mr = [
			(item, None, warehouses[0], batches[0], 1,  75, "2021-01-21"),
			(item, None, warehouses[0], batches[1], 1, 100, "2021-01-23"),
			(item, None, warehouses[0], batches[1], 1, 150, "2021-01-25"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mr, "Material Receipt"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(75.0, 75.0, 1.0, 1.0, '[[1.0, 75.0]]'),
			(100.0, 100.0, 1.0, 1.0, '[[1.0, 100.0]]'),
			(150.0, 250.0, 1.0, 2.0, '[[1.0, 100.0], [1.0, 150.0]]')
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Receipt Entries", columns
		))


		# Test Material Transfer Entries
		se_entry_list_mt = [
			(item, warehouses[0], warehouses[1], batches[1], 1, None, "2021-01-27"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mt, "Material Transfer"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		sle_details = sorted(sle_details, key=itemgetter(2))
		expected_sle_details = [
			(-100.0, 150.0, -1.0, 1.0, '[[1.0, 150.0]]'),
			(100.0, 100.0, 1.0, 1.0, '[[1.0, 100.0]]')
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Transfer Entries", columns
		))


		# Test Material Issue Entries
		se_entry_list_mi = [
			(item, warehouses[0], None, batches[1], 1, None, "2021-01-29"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mi, "Material Issue"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(-150.0, 0.0, -1.0, 0.0, '[[0, 150.0]]')
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Issue Entries", columns
		))


		# Test Backdated Material Receipt Entries
		se_entry_list_bd_mr = [
			(item, None, warehouses[1], batches[1], 1, 150, "2021-01-19"),
			(item, None, warehouses[1], batches[0], 1, 200, "2021-01-17")
		]
		# Prevent Repost from enqueuing (check RepostItemValuation.on_submit)
		frappe.flags.in_test = False
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_bd_mr, "Material Receipt"
		)
		frappe.flags.in_test = True
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(200.0, 200.0, 1.0, 1.0, '[[1.0, 200.0]]'),
			(150.0, 150.0, 1.0, 1.0, '[[1.0, 150.0]]')
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Backdated Material Receipt Entries", columns
		))


		# Run post-backdated-SE Repost SLE
		repost_entry_name = frappe.db.sql(f"""
			SELECT name FROM `tabRepost Item Valuation`
			WHERE voucher_no='{ses[0].name}'""")[0][0]
		repost_entry_doc = frappe.get_doc("Repost Item Valuation", repost_entry_name)
		repost_sl_entries(repost_entry_doc)


		# Material Issue to Test Backdated Material Receipt Entries
		se_entry_list_tbd_mi = [
			(item, warehouses[1], None, batches[1], 2, None, "2021-01-31")
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_tbd_mi, "Material Issue"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(-250.0, 0.0, -2.0, 0.0, '[[0, 125.0]]'),
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Issue to Test Backdated Entries", columns
		))


		# Run assertions
		for details in details_list:
			check_sle_details_against_expected(*details)


	def test_joint_item_valuation_stock_entry(self):
		"""
			Checking the valuation of a single item
			with three batches. Where the first batch
			uses batch-wise item valuation.

			Legacy valuation should ignore batches using
			batch-wise item valuation.
		"""
		suffix = get_unique_suffix()
		columns = [
				'stock_value_difference',
				'stock_value',
				'actual_qty',
				'qty_after_transaction',
				'stock_queue',
		]
		item, warehouses, batches = setup_item_valuation_test(
			valuation_method="FIFO", suffix=suffix,
			use_batchwise_valuation=[1, 0, 0], batches_list=['X', 'Y', 'Z']
		)

		def check_sle_details_against_expected(sle_details, expected_sle_details, detail, columns):
			for i, (sle_vals, ex_sle_vals) in enumerate(zip(sle_details, expected_sle_details)):
				for col, sle_val, ex_sle_val in zip(columns, sle_vals, ex_sle_vals):
					if col == 'stock_queue':
						sle_val = get_stock_value_from_q(sle_val)
						ex_sle_val = get_stock_value_from_q(ex_sle_val)
					self.assertEqual(
						sle_val, ex_sle_val,
						f"Incorrect {col} value on transaction #: {i} in {detail}"
					)

		# List used to defer assertions to prevent commits cause of error skipped rollback
		details_list = []


		# Test Material Receipt Entries
		se_entry_list_mr = [
			(item, None, warehouses[0], batches[0], 1, 150, "2021-01-21"),
			(item, None, warehouses[0], batches[1], 1, 50, "2021-01-23"),
			(item, None, warehouses[0], batches[2], 1, 100, "2021-01-25"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mr, "Material Receipt"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(150.0, 150.0, 1.0, 1.0, '[[1.0, 150.0]]'),
			(50.0, 50.0, 1.0, 1.0, '[[1.0, 50.0]]'),
			(100.0, 150.0, 1.0, 2.0, '[[1.0, 50.0], [1.0, 100.0]]'),
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Receipt Entries", columns
		))


		# Test Material Issue Entries
		se_entry_list_mi = [
			(item, warehouses[0], None, batches[2], 1, None, "2021-01-27"),
			(item, warehouses[0], None, batches[0], 1, None, "2021-01-29"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mi, "Material Issue"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(-50.0, 100.0, -1.0, 1.0, '[[1, 100.0]]'),
			(-150.0, 0.0, -1.0, 0.0, '[[0, 150.0]]')
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Issue Entries", columns
		))


		# Run assertions
		for details in details_list:
			check_sle_details_against_expected(*details)


	def test_legacy_item_valuation_stock_entry(self):
		suffix = get_unique_suffix()
		columns = [
				'stock_value_difference',
				'stock_value',
				'actual_qty',
				'qty_after_transaction',
				'stock_queue',
		]
		item, warehouses, batches = setup_item_valuation_test(
			valuation_method="FIFO", suffix=suffix, use_batchwise_valuation=0
		)

		def check_sle_details_against_expected(sle_details, expected_sle_details, detail, columns):
			for i, (sle_vals, ex_sle_vals) in enumerate(zip(sle_details, expected_sle_details)):
				for col, sle_val, ex_sle_val in zip(columns, sle_vals, ex_sle_vals):
					if col == 'stock_queue':
						sle_val = get_stock_value_from_q(sle_val)
						ex_sle_val = get_stock_value_from_q(ex_sle_val)
					self.assertEqual(
						sle_val, ex_sle_val,
						f"Incorrect {col} value on transaction #: {i} in {detail}"
					)

		# List used to defer assertions to prevent commits cause of error skipped rollback
		details_list = []


		# Test Material Receipt Entries
		se_entry_list_mr = [
			(item, None, warehouses[0], batches[0], 1,  50, "2021-01-21"),
			(item, None, warehouses[0], batches[1], 1, 100, "2021-01-23"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mr, "Material Receipt"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(50.0, 50.0, 1.0, 1.0, '[[1.0, 50.0]]'),
			(100.0, 150.0, 1.0, 2.0, '[[1.0, 50.0], [1.0, 100.0]]'),
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Receipt Entries", columns
		))


		# Test Material Issue Entries
		se_entry_list_mi = [
			(item, warehouses[0], None, batches[1], 1, None, "2021-01-29"),
		]
		ses = create_stock_entry_entries_for_batchwise_item_valuation_test(
			se_entry_list_mi, "Material Issue"
		)
		sle_details = fetch_sle_details_for_doc_list(ses, columns=columns, as_dict=0)
		expected_sle_details = [
			(-50.0, 100.0, -1.0, 1.0, '[[1, 100.0]]')
		]
		details_list.append((
			sle_details, expected_sle_details,
			"Material Issue Entries", columns
		))


		# Run assertions
		for details in details_list:
			check_sle_details_against_expected(*details)


def create_repack_entry(**args):
	args = frappe._dict(args)
	repack = frappe.new_doc("Stock Entry")
	repack.stock_entry_type = "Repack"
	repack.company = args.company or "_Test Company"
	repack.posting_date = args.posting_date
	repack.set_posting_time = 1
	repack.append("items", {
		"item_code": "_Test Item for Reposting",
		"s_warehouse": "Stores - _TC",
		"qty": 5,
		"conversion_factor": 1,
		"expense_account": "Stock Adjustment - _TC",
		"cost_center": "Main - _TC"
	})

	repack.append("items", {
		"item_code": "_Test Finished Item for Reposting",
		"t_warehouse": "Finished Goods - _TC",
		"qty": 1,
		"conversion_factor": 1,
		"expense_account": "Stock Adjustment - _TC",
		"cost_center": "Main - _TC"
	})

	repack.append("additional_costs", {
		"expense_account": "Freight and Forwarding Charges - _TC",
		"description": "transport cost",
		"amount": 40
	})

	repack.save()
	repack.submit()

	return repack

def create_product_bundle_item(new_item_code, packed_items):
	if not frappe.db.exists("Product Bundle", new_item_code):
		item = frappe.new_doc("Product Bundle")
		item.new_item_code = new_item_code

		for d in packed_items:
			item.append("items", {
				"item_code": d[0],
				"qty": d[1]
			})

		item.save()

def create_items():
	items = ["_Test Item for Reposting", "_Test Finished Item for Reposting",
		"_Test Subcontracted Item for Reposting", "_Test Bundled Item for Reposting"]
	for d in items:
		properties = {"valuation_method": "FIFO"}
		if d == "_Test Bundled Item for Reposting":
			properties.update({"is_stock_item": 0})
		elif d == "_Test Subcontracted Item for Reposting":
			properties.update({"is_sub_contracted_item": 1})

		make_item(d, properties=properties)

	return items

def setup_item_valuation_test(valuation_method, suffix, use_batchwise_valuation=1, batches_list=['X', 'Y']):
	from erpnext.stock.doctype.batch.batch import make_batch
	from erpnext.stock.doctype.item.test_item import make_item
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	item = make_item(
		f"IV - Test Item {valuation_method} {suffix}",
		dict(valuation_method=valuation_method, has_batch_no=1)
	)
	warehouses = [create_warehouse(f"IV - Test Warehouse {i}") for i in ['J', 'K']]
	batches = [f"IV - Test Batch {i} {valuation_method} {suffix}" for i in batches_list]

	for i, batch_id in enumerate(batches):
		if not frappe.db.exists("Batch", batch_id):
			ubw = use_batchwise_valuation
			if isinstance(use_batchwise_valuation, (list, tuple)):
				ubw = use_batchwise_valuation[i]
			make_batch(
				frappe._dict(
					batch_id=batch_id,
					item=item.item_code,
					use_batchwise_valuation=ubw
				)
			)

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
			rate=rate,
			qty=qty,
			item=item,
			warehouse=warehouse,
			against_blanket_order=0
		)

		dn = make_delivery_note(so.name)
		dn.items[0].batch_no = batch_no
		dn.insert()
		dn.submit()
		dns.append(dn)
	return dns

def fetch_sle_details_for_doc_list(doc_list, columns, as_dict=1):
	return frappe.db.sql(f"""
		SELECT { ', '.join(columns)}
		FROM `tabStock Ledger Entry`
		WHERE
			voucher_no IN %(voucher_nos)s
			and docstatus = 1
		ORDER BY timestamp(posting_date, posting_time) ASC
	""", dict(
		voucher_nos=[doc.name for doc in doc_list]
	), as_dict=as_dict)

def create_stock_reco_entries_for_batchwise_item_valuation_test(sr_entry_list, purpose):
	srs = []
	for item_code, warehouse, batch_no, qty, valuation_rate in sr_entry_list:
		sr = create_stock_reconciliation(
			purpose=purpose,
			warehouse=warehouse,
			item_code=item_code,
			qty=qty,
			rate=valuation_rate,
			batch_no=batch_no
		)
		srs.append(sr)
	return srs

def get_stock_value_from_q(q):
	return sum(r*q for r,q in json.loads(q))

def create_stock_entry_entries_for_batchwise_item_valuation_test(se_entry_list, purpose):
	ses = []
	for item, source, target, batch, qty, rate, posting_date in se_entry_list:
		args = dict(
			item_code=item,
			qty=qty,
			company="_Test Company",
			batch_no=batch,
			posting_date=posting_date,
			purpose=purpose
		)

		if purpose == "Material Receipt":
			args.update(
				dict(to_warehouse=target, rate=rate)
			)

		elif purpose == "Material Issue":
			args.update(
				dict(from_warehouse=source)
			)

		elif purpose == "Material Transfer":
			args.update(
				dict(from_warehouse=source, to_warehouse=target)
			)

		else:
			raise ValueError(f"Invalid purpose: {purpose}")
		ses.append(make_stock_entry(**args))

	return ses

def get_unique_suffix():
	# Used to isolate valuation sensitive
	# tests to prevent future tests from failing.
	return str(uuid4())[:8].upper()
