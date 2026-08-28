# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import copy
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, flt, now, nowtime, today

from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import update_gl_entries_after
from erpnext.assets.doctype.asset.test_asset import create_fixed_asset_item
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	get_gl_entries,
	make_purchase_receipt,
)
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_serial_nos_from_bundle,
)
from erpnext.stock.serial_batch_bundle import SerialNoValuation
from erpnext.tests.utils import ERPNextTestSuite


class TestLandedCostVoucher(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Currency Exchange")

	def test_get_vendor_invoices_runs(self):
		# get_vendor_invoice_query filters unclaimed vendor invoices; the threshold moved from a HAVING
		# (which referenced a SELECT alias with no GROUP BY -- invalid on Postgres) to a WHERE.
		from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import get_vendor_invoices

		pi = make_purchase_invoice(item_code="_Test Non Stock Item", qty=1, rate=100)

		rows = get_vendor_invoices(
			"Purchase Invoice", "", "name", 0, 20, {"company": "_Test Company", "name": pi.name}
		)
		self.assertTrue(any(r[0] == pi.name for r in rows))

	def test_landed_cost_voucher(self):
		frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			get_multiple_items=True,
			get_taxes_and_charges=True,
		)

		last_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": pr.doctype,
				"voucher_no": pr.name,
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
				"is_cancelled": 0,
			},
			fieldname=["qty_after_transaction", "stock_value"],
			as_dict=1,
		)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		pr_lc_value = frappe.db.get_value(
			"Purchase Receipt Item", {"parent": pr.name}, "landed_cost_voucher_amount"
		)
		self.assertEqual(pr_lc_value, 25.0)

		last_sle_after_landed_cost = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": pr.doctype,
				"voucher_no": pr.name,
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
				"is_cancelled": 0,
			},
			fieldname=["qty_after_transaction", "stock_value"],
			as_dict=1,
		)

		self.assertEqual(last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction)
		self.assertEqual(last_sle_after_landed_cost.stock_value - last_sle.stock_value, 25.0)

		# assert after submit
		self.assertPurchaseReceiptLCVGLEntries(pr)

		# Mess up cancelled SLE modified timestamp to check
		# if they aren't effective in any business logic.
		frappe.db.set_value(
			"Stock Ledger Entry",
			{"is_cancelled": 1, "voucher_type": pr.doctype, "voucher_no": pr.name},
			"is_cancelled",
			1,
			modified=add_to_date(now(), hours=1, as_datetime=True, as_string=True),
		)

		items, warehouses = pr.get_items_and_warehouses()
		update_gl_entries_after(pr.posting_date, pr.posting_time, warehouses, items, company=pr.company)

		# reassert after reposting
		self.assertPurchaseReceiptLCVGLEntries(pr)

	def assertPurchaseReceiptLCVGLEntries(self, pr):
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		fixed_asset_account = get_inventory_account(pr.company, pr.get("items")[1].warehouse)

		if stock_in_hand_account == fixed_asset_account:
			expected_values = {
				stock_in_hand_account: [800.0, 0.0],
				"Stock Received But Not Billed - TCP1": [0.0, 500.0],
				"Expenses Included In Valuation - TCP1": [0.0, 50.0],
				"_Test Account Customs Duty - TCP1": [0.0, 150],
				"_Test Account Shipping Charges - TCP1": [0.0, 100.00],
			}
		else:
			expected_values = {
				stock_in_hand_account: [400.0, 0.0],
				fixed_asset_account: [400.0, 0.0],
				"Stock Received But Not Billed - TCP1": [0.0, 500.0],
				"Expenses Included In Valuation - TCP1": [0.0, 300.0],
			}

		for gle in gl_entries:
			if not gle.get("is_cancelled"):
				self.assertEqual(
					expected_values[gle.account][0], gle.debit, msg=f"incorrect debit for {gle.account}"
				)
				self.assertEqual(
					expected_values[gle.account][1], gle.credit, msg=f"incorrect credit for {gle.account}"
				)

	def test_landed_cost_voucher_stock_impact(self):
		"Test impact of LCV on future stock balances."
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("LCV Stock Item", {"is_stock_item": 1})
		warehouse = "Stores - _TC"

		pr1 = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			qty=500,
			rate=80,
			posting_date=add_days(frappe.utils.nowdate(), -2),
		)
		pr2 = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			qty=100,
			rate=80,
			posting_date=frappe.utils.nowdate(),
		)

		last_sle = frappe.db.get_value(  # SLE of second PR
			"Stock Ledger Entry",
			{
				"voucher_type": pr2.doctype,
				"voucher_no": pr2.name,
				"item_code": item.name,
				"warehouse": warehouse,
				"is_cancelled": 0,
			},
			fieldname=["qty_after_transaction", "stock_value"],
			as_dict=1,
		)

		create_landed_cost_voucher("Purchase Receipt", pr1.name, pr1.company)

		last_sle_after_landed_cost = frappe.db.get_value(  # SLE of second PR after LCV's effect
			"Stock Ledger Entry",
			{
				"voucher_type": pr2.doctype,
				"voucher_no": pr2.name,
				"item_code": item.name,
				"warehouse": warehouse,
				"is_cancelled": 0,
			},
			fieldname=["qty_after_transaction", "stock_value"],
			as_dict=1,
		)

		self.assertEqual(last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction)
		self.assertEqual(last_sle_after_landed_cost.stock_value - last_sle.stock_value, 50.0)

	def test_lcv_validates_company(self):
		from erpnext import is_perpetual_inventory_enabled
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.landed_cost_voucher.landed_cost_voucher import (
			IncorrectCompanyValidationError,
		)

		company_a = "_Test Company"
		company_b = "_Test Company with perpetual inventory"

		srbnb = create_account(
			account_name="Stock Received But Not Billed",
			account_type="Stock Received But Not Billed",
			parent_account="Stock Liabilities - _TC",
			company=company_a,
			account_currency="INR",
		)

		epi = is_perpetual_inventory_enabled(company_a)
		company_doc = frappe.get_doc("Company", company_a)
		old_inventory_account = company_doc.default_inventory_account
		company_doc.enable_perpetual_inventory = 1
		company_doc.stock_received_but_not_billed = srbnb
		company_doc.default_inventory_account = "Stock In Hand - _TC"
		company_doc.save()

		pr = make_purchase_receipt(
			company=company_a,
			warehouse="Stores - _TC",
			qty=1,
			rate=100,
		)

		lcv = make_landed_cost_voucher(
			company=company_b,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=50,
			do_not_save=True,
		)

		self.assertRaises(IncorrectCompanyValidationError, lcv.validate_receipt_documents)
		lcv.company = company_a

		self.assertRaises(IncorrectCompanyValidationError, lcv.validate_expense_accounts)
		lcv.taxes[0].expense_account = get_expense_account(company_a)

		lcv.save()
		distribute_landed_cost_on_items(lcv)
		lcv.submit()

		frappe.db.set_value(
			"Company",
			company_a,
			{"enable_perpetual_inventory": epi, "default_inventory_account": old_inventory_account},
		)
		frappe.local.enable_perpetual_inventory = {}

	def test_landed_cost_voucher_for_zero_purchase_rate(self):
		"Test impact of LCV on future stock balances."
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("LCV Stock Item", {"is_stock_item": 1})
		warehouse = "Stores - _TC"

		pr = make_purchase_receipt(
			item_code=item.name,
			warehouse=warehouse,
			qty=10,
			rate=0,
			posting_date=add_days(frappe.utils.nowdate(), -2),
		)

		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Purchase Receipt", "voucher_no": pr.name, "is_cancelled": 0},
				"stock_value_difference",
			),
			0,
		)

		lcv = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=100,
			distribute_charges_based_on="Distribute Manually",
			do_not_save=True,
		)

		lcv.get_items_from_purchase_receipts()
		lcv.items[0].applicable_charges = 100
		lcv.save()
		lcv.submit()

		self.assertTrue(
			frappe.db.exists(
				"Stock Ledger Entry",
				{"voucher_type": "Purchase Receipt", "voucher_no": pr.name, "is_cancelled": 0},
			)
		)
		self.assertEqual(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Purchase Receipt", "voucher_no": pr.name, "is_cancelled": 0},
				"stock_value_difference",
			),
			100,
		)

	def test_landed_cost_voucher_against_purchase_invoice(self):
		pi = make_purchase_invoice(
			update_stock=1,
			posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(),
			cash_bank_account="Cash - TCP1",
			company="_Test Company with perpetual inventory",
			supplier_warehouse="Work In Progress - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
		)

		last_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": pi.doctype,
				"voucher_no": pi.name,
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
			},
			fieldname=["qty_after_transaction", "stock_value"],
			as_dict=1,
		)

		create_landed_cost_voucher("Purchase Invoice", pi.name, pi.company)

		pi_lc_value = frappe.db.get_value(
			"Purchase Invoice Item", {"parent": pi.name}, "landed_cost_voucher_amount"
		)

		self.assertEqual(pi_lc_value, 50.0)

		last_sle_after_landed_cost = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": pi.doctype,
				"voucher_no": pi.name,
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
			},
			fieldname=["qty_after_transaction", "stock_value"],
			as_dict=1,
		)

		self.assertEqual(last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction)

		self.assertEqual(last_sle_after_landed_cost.stock_value - last_sle.stock_value, 50.0)

		gl_entries = get_gl_entries("Purchase Invoice", pi.name)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(pi.company, pi.get("items")[0].warehouse)

		expected_values = {
			stock_in_hand_account: [300.0, 0.0],
			"Creditors - TCP1": [0.0, 250.0],
			"Expenses Included In Valuation - TCP1": [0.0, 50.0],
		}

		for gle in gl_entries:
			if not gle.get("is_cancelled"):
				self.assertEqual(expected_values[gle.account][0], gle.debit)
				self.assertEqual(expected_values[gle.account][1], gle.credit)

	def test_landed_cost_voucher_for_serialized_item(self):
		frappe.db.set_value("Item", "_Test Serialized Item", "serial_no_series", "SNJJ.###")

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			get_multiple_items=True,
			get_taxes_and_charges=True,
			do_not_submit=True,
		)

		pr.items[0].item_code = "_Test Serialized Item"
		pr.submit()
		pr.load_from_db()

		serial_no = get_serial_nos_from_bundle(pr.items[0].serial_and_batch_bundle)[0]

		sn_obj = SerialNoValuation(
			sle=frappe._dict(
				{
					"posting_date": today(),
					"posting_time": nowtime(),
					"item_code": "_Test Serialized Item",
					"warehouse": "Stores - TCP1",
					"serial_nos": [serial_no],
				}
			)
		)

		serial_no_rate = sn_obj.get_incoming_rate_of_serial_no(serial_no)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		sn_obj = SerialNoValuation(
			sle=frappe._dict(
				{
					"posting_date": today(),
					"posting_time": nowtime(),
					"item_code": "_Test Serialized Item",
					"warehouse": "Stores - TCP1",
					"serial_nos": [serial_no],
				}
			)
		)

		new_serial_no_rate = sn_obj.get_incoming_rate_of_serial_no(serial_no)

		self.assertEqual(new_serial_no_rate - serial_no_rate, 5.0)

	def test_serialized_lcv_delivered(self):
		"""In some cases you'd want to deliver before you can know all the
		landed costs, this should be allowed for serial nos too.

		Case:
		                - receipt a serial no @ X rate
		                - delivery the serial no @ X rate
		                - add LCV to receipt X + Y
		                - LCV should be successful
		                - delivery should reflect X+Y valuation.
		"""
		serial_no = "LCV_TEST_SR_NO"
		item_code = "_Test Serialized Item"
		warehouse = "Stores - TCP1"

		if not frappe.db.exists("Serial No", serial_no):
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"item_code": item_code,
					"serial_no": serial_no,
					"company": "_Test Company",
				}
			).insert()

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse=warehouse,
			qty=1,
			rate=200,
			item_code=item_code,
			serial_no=[serial_no],
		)

		sn_obj = SerialNoValuation(
			sle=frappe._dict(
				{
					"posting_date": today(),
					"posting_time": nowtime(),
					"item_code": "_Test Serialized Item",
					"warehouse": "Stores - TCP1",
					"serial_nos": [serial_no],
				}
			)
		)

		serial_no_rate = sn_obj.get_incoming_rate_of_serial_no(serial_no)

		# deliver it before creating LCV
		dn = create_delivery_note(
			item_code=item_code,
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			serial_no=[serial_no],
			qty=1,
			rate=500,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
		)

		charges = 10
		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company, charges=charges)
		new_purchase_rate = serial_no_rate + charges

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			filters={
				"voucher_no": dn.name,
				"voucher_type": dn.doctype,
				"is_cancelled": 0,  # LCV cancels with same name.
			},
			fieldname="stock_value_difference",
		)

		# reposting should update the purchase rate in future delivery
		self.assertEqual(stock_value_difference, -new_purchase_rate)

	def test_landed_cost_voucher_for_odd_numbers(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			do_not_save=True,
		)
		pr.items[0].cost_center = "Main - TCP1"
		for _x in range(2):
			pr.append(
				"items",
				{
					"item_code": "_Test Item",
					"warehouse": "Stores - TCP1",
					"cost_center": "Main - TCP1",
					"qty": 5,
					"rate": 50,
				},
			)
		pr.submit()

		lcv = create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company, 123.22)

		self.assertEqual(flt(lcv.items[0].applicable_charges, 2), 41.07)
		self.assertEqual(flt(lcv.items[2].applicable_charges, 2), 41.08)

	def test_multiple_landed_cost_voucher_against_pr(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Stores - TCP1",
			do_not_save=True,
		)

		pr.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
				"cost_center": "Main - TCP1",
				"qty": 5,
				"rate": 100,
			},
		)

		pr.submit()

		lcv1 = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=100,
			do_not_save=True,
		)

		lcv1.insert()
		lcv1.set("items", [lcv1.get("items")[0]])
		distribute_landed_cost_on_items(lcv1)

		lcv1.submit()

		lcv2 = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=100,
			do_not_save=True,
		)

		lcv2.insert()
		lcv2.set("items", [lcv2.get("items")[1]])
		distribute_landed_cost_on_items(lcv2)

		lcv2.submit()

		pr.load_from_db()

		self.assertEqual(pr.items[0].landed_cost_voucher_amount, 100)
		self.assertEqual(pr.items[1].landed_cost_voucher_amount, 100)

	def test_multi_currency_lcv(self):
		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import save_new_records

		save_new_records(self.globalTestRecords["Currency Exchange"])

		## Create USD Shipping charges_account
		usd_shipping = create_account(
			account_name="Shipping Charges USD",
			parent_account="Duties and Taxes - TCP1",
			company="_Test Company with perpetual inventory",
			account_currency="USD",
		)

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Stores - TCP1",
		)
		pr.submit()

		lcv = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=100,
			do_not_save=True,
		)

		lcv.append(
			"taxes", {"description": "Shipping Charges", "expense_account": usd_shipping, "amount": 10}
		)

		lcv.save()
		lcv.submit()
		pr.load_from_db()

		# Considering exchange rate from USD to INR as 62.9
		self.assertEqual(lcv.total_taxes_and_charges, 729)
		self.assertEqual(pr.items[0].landed_cost_voucher_amount, 729)

		gl_entries = frappe.get_all(
			"GL Entry",
			fields=["account", "credit", "credit_in_account_currency"],
			filters={
				"voucher_no": pr.name,
				"account": ("in", ["Shipping Charges USD - TCP1", "Expenses Included In Valuation - TCP1"]),
			},
		)

		expected_gl_entries = {
			"Shipping Charges USD - TCP1": [629, 10],
			"Expenses Included In Valuation - TCP1": [100, 100],
		}

		for entry in gl_entries:
			amounts = expected_gl_entries.get(entry.account)
			self.assertEqual(entry.credit, amounts[0])
			self.assertEqual(entry.credit_in_account_currency, amounts[1])

	def test_asset_lcv(self):
		"Check if LCV for an Asset updates the Assets Net Purchase Amount correctly."
		frappe.db.set_value(
			"Company", "_Test Company", "capital_work_in_progress_account", "CWIP Account - _TC"
		)

		if not frappe.db.exists("Item", "Macbook Pro"):
			create_fixed_asset_item()

		pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=50000)

		# check if draft asset was created
		assets = frappe.db.get_all("Asset", filters={"purchase_receipt": pr.name})
		self.assertEqual(len(assets), 1)

		lcv = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=80,
			expense_account="Expenses Included In Valuation - _TC",
		)

		lcv.save()
		lcv.submit()

		# lcv updates amount in draft asset
		self.assertEqual(frappe.db.get_value("Asset", assets[0].name, "net_purchase_amount"), 50080)

		# tear down
		lcv.cancel()
		pr.cancel()

	def test_landed_cost_voucher_with_serial_batch_for_legacy_pr(self):
		from erpnext.stock.doctype.item.test_item import make_item

		frappe.flags.ignore_serial_batch_bundle_validation = True
		frappe.flags.use_serial_and_batch_fields = True
		sn_item = "Test Landed Cost Voucher Serial NO for Legacy PR"
		batch_item = "Test Landed Cost Voucher Batch NO for Legacy PR"
		sn_item_doc = make_item(
			sn_item,
			{
				"has_serial_no": 1,
				"serial_no_series": "SN-TLCVSNO-.####",
				"is_stock_item": 1,
			},
		)

		batch_item_doc = make_item(
			batch_item,
			{
				"has_batch_no": 1,
				"batch_number_series": "BATCH-TLCVSNO-.####",
				"create_new_batch": 1,
				"is_stock_item": 1,
			},
		)

		serial_nos = [
			"SN-TLCVSNO-0001",
			"SN-TLCVSNO-0002",
			"SN-TLCVSNO-0003",
			"SN-TLCVSNO-0004",
			"SN-TLCVSNO-0005",
		]

		for sn in serial_nos:
			if not frappe.db.exists("Serial No", sn):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": sn_item,
						"serial_no": sn,
						"company": "_Test Company",
					}
				)
				sn_doc.insert()

		if not frappe.db.exists("Batch", "BATCH-TLCVSNO-0001"):
			batch_doc = frappe.get_doc(
				{
					"doctype": "Batch",
					"item": batch_item,
					"batch_id": "BATCH-TLCVSNO-0001",
				}
			)
			batch_doc.insert()

		warehouse = "_Test Warehouse - _TC"
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		pr = make_purchase_receipt(
			company=company,
			warehouse=warehouse,
			item_code=sn_item,
			qty=5,
			rate=100,
			uom=sn_item_doc.stock_uom,
			stock_uom=sn_item_doc.stock_uom,
			do_not_submit=True,
		)

		pr.append(
			"items",
			{
				"item_code": batch_item,
				"item_name": batch_item,
				"description": "Test Batch Item",
				"uom": batch_item_doc.stock_uom,
				"stock_uom": batch_item_doc.stock_uom,
				"qty": 5,
				"rate": 100,
				"warehouse": warehouse,
			},
		)

		pr.submit()
		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 100)
			self.assertFalse(row.serial_no)
			self.assertFalse(row.batch_no)
			self.assertFalse(row.serial_and_batch_bundle)

			if row.item_code == sn_item:
				row.db_set("serial_no", ", ".join(serial_nos))
			else:
				row.db_set("batch_no", "BATCH-TLCVSNO-0001")

		for sn in serial_nos:
			sn_doc = frappe.get_doc("Serial No", sn)
			sn_doc.db_set(
				{
					"warehouse": warehouse,
					"status": "Active",
				}
			)

		batch_doc.db_set(
			{
				"batch_qty": 5,
			}
		)

		frappe.flags.ignore_serial_batch_bundle_validation = False
		frappe.flags.use_serial_and_batch_fields = False

		lcv = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=20,
			distribute_charges_based_on="Qty",
			do_not_save=True,
		)

		lcv.get_items_from_purchase_receipts()
		lcv.save()
		lcv.submit()

		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 102)
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertEqual(
				row.valuation_rate,
				frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "avg_rate"),
			)

		lcv.cancel()
		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 100)
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertEqual(
				row.valuation_rate,
				frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "avg_rate"),
			)

	def test_do_not_validate_landed_cost_voucher_with_serial_batch_for_legacy_pr(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_auto_batch_nos

		frappe.flags.ignore_serial_batch_bundle_validation = True
		frappe.flags.use_serial_and_batch_fields = True
		sn_item = "Test Don't Validate Landed Cost Voucher Serial NO for Legacy PR"
		batch_item = "Test Don't Validate Landed Cost Voucher Batch NO for Legacy PR"
		sn_item_doc = make_item(
			sn_item,
			{
				"has_serial_no": 1,
				"serial_no_series": "SN-TDVLCVSNO-.####",
				"is_stock_item": 1,
			},
		)

		batch_item_doc = make_item(
			batch_item,
			{
				"has_batch_no": 1,
				"batch_number_series": "BATCH-TDVLCVSNO-.####",
				"create_new_batch": 1,
				"is_stock_item": 1,
			},
		)

		serial_nos = [
			"SN-TDVLCVSNO-0001",
			"SN-TDVLCVSNO-0002",
			"SN-TDVLCVSNO-0003",
			"SN-TDVLCVSNO-0004",
			"SN-TDVLCVSNO-0005",
		]

		for sn in serial_nos:
			if not frappe.db.exists("Serial No", sn):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": sn_item,
						"serial_no": sn,
						"company": "_Test Company",
					}
				)
				sn_doc.insert()

		if not frappe.db.exists("Batch", "BATCH-TDVLCVSNO-0001"):
			batch_doc = frappe.get_doc(
				{
					"doctype": "Batch",
					"item": batch_item,
					"batch_id": "BATCH-TDVLCVSNO-0001",
				}
			)
			batch_doc.insert()

		warehouse = "_Test Warehouse - _TC"
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		pr = make_purchase_receipt(
			company=company,
			warehouse=warehouse,
			item_code=sn_item,
			qty=5,
			rate=100,
			uom=sn_item_doc.stock_uom,
			stock_uom=sn_item_doc.stock_uom,
			do_not_submit=True,
		)

		pr.append(
			"items",
			{
				"item_code": batch_item,
				"item_name": batch_item,
				"description": "Test Batch Item",
				"uom": batch_item_doc.stock_uom,
				"stock_uom": batch_item_doc.stock_uom,
				"qty": 5,
				"rate": 100,
				"warehouse": warehouse,
			},
		)

		pr.submit()
		pr.reload()

		for sn in serial_nos:
			sn_doc = frappe.get_doc("Serial No", sn)
			sn_doc.db_set(
				{
					"warehouse": warehouse,
					"status": "Active",
				}
			)

		batch_doc.db_set(
			{
				"batch_qty": 5,
			}
		)

		for row in pr.items:
			if row.item_code == sn_item:
				row.db_set("serial_no", ", ".join(serial_nos))
			else:
				row.db_set("batch_no", "BATCH-TDVLCVSNO-0001")

		stock_ledger_entries = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": pr.name})
		for sle in stock_ledger_entries:
			doc = frappe.get_doc("Stock Ledger Entry", sle.name)
			if doc.item_code == sn_item:
				doc.db_set("serial_no", ", ".join(serial_nos))
			else:
				doc.db_set("batch_no", "BATCH-TDVLCVSNO-0001")

		dn = create_delivery_note(
			company=company,
			warehouse=warehouse,
			item_code=sn_item,
			qty=5,
			rate=100,
			uom=sn_item_doc.stock_uom,
			stock_uom=sn_item_doc.stock_uom,
			do_not_submit=True,
		)

		dn.append(
			"items",
			{
				"item_code": batch_item,
				"item_name": batch_item,
				"description": "Test Batch Item",
				"uom": batch_item_doc.stock_uom,
				"stock_uom": batch_item_doc.stock_uom,
				"qty": 5,
				"rate": 100,
				"warehouse": warehouse,
			},
		)

		dn.submit()

		stock_ledger_entries = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": dn.name})
		for sle in stock_ledger_entries:
			doc = frappe.get_doc("Stock Ledger Entry", sle.name)
			if doc.item_code == sn_item:
				doc.db_set("serial_no", ", ".join(serial_nos))
			else:
				doc.db_set("batch_no", "BATCH-TDVLCVSNO-0001")

		available_batches = get_auto_batch_nos(
			frappe._dict(
				{
					"item_code": batch_item,
					"warehouse": warehouse,
					"batch_no": ["BATCH-TDVLCVSNO-0001"],
					"consider_negative_batches": True,
				}
			)
		)[0]

		self.assertFalse(available_batches.get("qty"))

		frappe.flags.ignore_serial_batch_bundle_validation = False
		frappe.flags.use_serial_and_batch_fields = False

		lcv = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=20,
			distribute_charges_based_on="Qty",
			do_not_save=True,
		)

		lcv.get_items_from_purchase_receipts()
		lcv.save()
		lcv.submit()

		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 102)
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertEqual(
				row.valuation_rate,
				frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "avg_rate"),
			)

		lcv.cancel()
		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 100)
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertEqual(
				row.valuation_rate,
				frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "avg_rate"),
			)

	def test_do_not_validate_against_landed_cost_voucher_for_serial_for_legacy_pr(self):
		from erpnext.stock.doctype.item.test_item import make_item

		frappe.flags.ignore_serial_batch_bundle_validation = True
		frappe.flags.use_serial_and_batch_fields = True
		sn_item = "Test Don't Validate Against LCV For Serial NO for Legacy PR"
		sn_item_doc = make_item(
			sn_item,
			{
				"has_serial_no": 1,
				"serial_no_series": "SN-ALCVTDVLCVSNO-.####",
				"is_stock_item": 1,
			},
		)

		serial_nos = [
			"SN-ALCVTDVLCVSNO-0001",
			"SN-ALCVTDVLCVSNO-0002",
			"SN-ALCVTDVLCVSNO-0003",
			"SN-ALCVTDVLCVSNO-0004",
			"SN-ALCVTDVLCVSNO-0005",
		]

		for sn in serial_nos:
			if not frappe.db.exists("Serial No", sn):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": sn_item,
						"serial_no": sn,
						"company": "_Test Company",
					}
				)
				sn_doc.insert()

		warehouse = "_Test Warehouse - _TC"
		company = frappe.db.get_value("Warehouse", warehouse, "company")

		pr = make_purchase_receipt(
			company=company,
			warehouse=warehouse,
			item_code=sn_item,
			qty=5,
			rate=100,
			uom=sn_item_doc.stock_uom,
			stock_uom=sn_item_doc.stock_uom,
		)

		pr.reload()

		for sn in serial_nos:
			sn_doc = frappe.get_doc("Serial No", sn)
			sn_doc.db_set(
				{
					"warehouse": warehouse,
					"status": "Active",
				}
			)

		for row in pr.items:
			if row.item_code == sn_item:
				row.db_set("serial_no", ", ".join(serial_nos))

		stock_ledger_entries = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": pr.name})
		for sle in stock_ledger_entries:
			doc = frappe.get_doc("Stock Ledger Entry", sle.name)
			if doc.item_code == sn_item:
				doc.db_set("serial_no", ", ".join(serial_nos))

		dn = create_delivery_note(
			company=company,
			warehouse=warehouse,
			item_code=sn_item,
			qty=5,
			rate=100,
			uom=sn_item_doc.stock_uom,
			stock_uom=sn_item_doc.stock_uom,
		)

		stock_ledger_entries = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": dn.name})
		for sle in stock_ledger_entries:
			doc = frappe.get_doc("Stock Ledger Entry", sle.name)
			if doc.item_code == sn_item:
				doc.db_set("serial_no", ", ".join(serial_nos))

		frappe.flags.ignore_serial_batch_bundle_validation = False
		frappe.flags.use_serial_and_batch_fields = False

		lcv = make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=20,
			distribute_charges_based_on="Qty",
			do_not_save=True,
		)

		lcv.get_items_from_purchase_receipts()
		lcv.save()
		lcv.submit()

		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 104)
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertEqual(
				row.valuation_rate,
				frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "avg_rate"),
			)

		lcv.cancel()
		pr.reload()

		for row in pr.items:
			self.assertEqual(row.valuation_rate, 100)
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertEqual(
				row.valuation_rate,
				frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "avg_rate"),
			)

	def test_lcv_for_work_order_scr(self):
		from erpnext.controllers.tests.test_subcontracting_controller import (
			get_rm_items,
			get_subcontracting_order,
			make_stock_in_entry,
			make_stock_transfer_entry,
		)
		from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
			make_subcontracting_receipt,
		)

		wo_fg_item = "Test Item FG LCV WO 1"
		wo_rm_items = ["Test Item RM LCV WO 1", "Test Item RM LCV WO 2"]

		scr_fg_item = "Test Item FG LCV SCR 1"
		scr_rm_items = ["Test Item RM LCV SCR 1", "Test Item RM LCV SCR 2"]
		company = "_Test Company with perpetual inventory"
		warehouse = frappe.get_value("Warehouse", {"company": company}, "name")
		wip_warehouse = frappe.get_value(
			"Warehouse",
			{"company": company, "name": ("!=", warehouse)},
			"name",
		)

		service_item = "Test Service Item LCV"

		for item in scr_rm_items + wo_rm_items + [wo_fg_item, scr_fg_item, service_item]:
			make_item(
				item,
				{
					"is_stock_item": 1 if item != service_item else 0,
					"stock_uom": "Nos",
					"company": company,
					"is_sub_contracted_item": 1 if item == scr_fg_item else 0,
				},
			)

		for item in scr_rm_items + wo_rm_items:
			make_stock_entry(
				item_code=item,
				company=company,
				to_warehouse=warehouse,
				qty=10,
				rate=100,
			)

		make_bom(item=wo_fg_item, company=company, raw_materials=wo_rm_items)

		make_bom(item=scr_fg_item, company=company, raw_materials=scr_rm_items)

		service_items = [
			{
				"warehouse": warehouse,
				"item_code": service_item,
				"qty": 10,
				"rate": 100,
				"fg_item": scr_fg_item,
				"fg_item_qty": 10,
				"company": company,
				"supplier_warehouse": wip_warehouse,
			},
		]
		sco = get_subcontracting_order(
			service_items=service_items,
			company=company,
			warehouse=warehouse,
			supplier_warehouse=wip_warehouse,
		)

		rm_items = get_rm_items(sco.supplied_items)
		itemwise_details = make_stock_in_entry(rm_items=rm_items)

		make_stock_transfer_entry(
			sco_no=sco.name,
			rm_items=rm_items,
			itemwise_details=copy.deepcopy(itemwise_details),
		)
		scr = make_subcontracting_receipt(sco.name)
		scr.save()
		scr.submit()

		wo_order = make_wo_order_test_record(
			production_item=wo_fg_item,
			planned_start_date=now(),
			qty=10,
			source_warehouse=warehouse,
			wip_warehouse=wip_warehouse,
			fg_warehouse=warehouse,
			company=company,
		)

		se = frappe.get_doc(make_stock_entry_for_wo(wo_order.name, "Material Transfer for Manufacture", 10))
		se.submit()

		se = frappe.get_doc(make_stock_entry_for_wo(wo_order.name, "Manufacture", 10))
		se.submit()

		lcv = make_landed_cost_voucher(
			company=scr.company,
			receipt_document_type="Subcontracting Receipt",
			receipt_document=scr.name,
			distribute_charges_based_on="Distribute Manually",
			do_not_save=True,
		)

		lcv.append(
			"purchase_receipts",
			{
				"receipt_document_type": "Stock Entry",
				"receipt_document": se.name,
			},
		)

		lcv.get_items_from_purchase_receipts()

		accounts = [
			"Electricity Charges - TCP1",
			"Rent Charges - TCP1",
		]

		for account in accounts:
			if not frappe.db.exists("Account", account):
				create_account(
					account_name=account.split(" - ")[0],
					account_type="Expense Account",
					parent_account="Direct Expenses - TCP1",
					company=company,
				)

		for account in accounts:
			lcv.append(
				"taxes",
				{
					"description": f"{account} Charges",
					"expense_account": account,
					"amount": 100,
				},
			)

		for row in lcv.items:
			row.applicable_charges = 100.00

		lcv.save()
		lcv.submit()

		for d in lcv.purchase_receipts:
			gl_entries = frappe.get_all(
				"GL Entry",
				filters={
					"voucher_type": d.receipt_document_type,
					"voucher_no": d.receipt_document,
					"is_cancelled": 0,
					"account": ("in", accounts),
				},
				fields=["account", "credit"],
			)

			for gl in gl_entries:
				self.assertEqual(gl.credit, 50.0)

		lcv.cancel()

		for d in lcv.purchase_receipts:
			gl_entries = frappe.get_all(
				"GL Entry",
				filters={
					"voucher_type": d.receipt_document_type,
					"voucher_no": d.receipt_document,
					"is_cancelled": 0,
					"account": ("in", accounts),
				},
				fields=["account", "credit"],
			)

			self.assertFalse(gl_entries)

	@patch.dict(frappe.flags, {"dont_execute_stock_reposts": True})
	def test_landed_cost_voucher_does_not_change_qty_across_stock_reco(self):
		"""LCV cost updates must not change quantity after a batch stock reconciliation."""
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		company = "_Test Company with perpetual inventory"
		warehouse = "Stores - TCP1"
		item = make_item(
			properties={"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "LCVRECO-.####"}
		).name
		first_batch = frappe.get_doc({"doctype": "Batch", "item": item}).insert().name
		second_batch = frappe.get_doc({"doctype": "Batch", "item": item}).insert().name

		receipt = make_purchase_receipt(
			company=company,
			warehouse=warehouse,
			item_code=item,
			qty=100,
			rate=10,
			use_serial_batch_fields=1,
			batch_no=first_batch,
			posting_date=add_days(today(), -30),
		)
		make_purchase_receipt(
			company=company,
			warehouse=warehouse,
			item_code=item,
			qty=60,
			rate=10,
			use_serial_batch_fields=1,
			batch_no=second_batch,
			posting_date=add_days(today(), -28),
		)
		create_stock_reconciliation(
			company=company,
			warehouse=warehouse,
			item_code=item,
			qty=55,
			rate=10,
			use_serial_batch_fields=1,
			batch_no=second_batch,
			posting_date=add_days(today(), -20),
		)

		def closing_balance():
			return frappe.get_all(
				"Stock Ledger Entry",
				filters={"item_code": item, "warehouse": warehouse, "is_cancelled": 0},
				fields=["qty_after_transaction"],
				order_by="posting_datetime desc, creation desc",
				limit=1,
			)[0].qty_after_transaction

		balance_before = closing_balance()
		create_landed_cost_voucher("Purchase Receipt", receipt.name, company)

		self.assertEqual(closing_balance(), balance_before)


def make_landed_cost_voucher(**args):
	args = frappe._dict(args)
	ref_doc = frappe.get_doc(args.receipt_document_type, args.receipt_document)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = args.company or "_Test Company"
	lcv.distribute_charges_based_on = args.distribute_charges_based_on or "Amount"
	expense_account = get_expense_account(args.company or "_Test Company")

	lcv.set(
		"purchase_receipts",
		[
			{
				"receipt_document_type": args.receipt_document_type,
				"receipt_document": args.receipt_document,
				"supplier": ref_doc.get("supplier"),
				"posting_date": ref_doc.get("posting_date"),
				"grand_total": ref_doc.get("grand_total"),
			}
		],
	)

	if args.charges:
		lcv.set(
			"taxes",
			[
				{
					"description": "Shipping Charges",
					"expense_account": args.expense_account or expense_account,
					"amount": args.charges,
				}
			],
		)

	if not args.do_not_save:
		lcv.insert()
		if not args.do_not_submit:
			lcv.submit()

	return lcv


def create_landed_cost_voucher(receipt_document_type, receipt_document, company, charges=50):
	ref_doc = frappe.get_doc(receipt_document_type, receipt_document)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = company
	lcv.distribute_charges_based_on = "Amount"
	expense_account = get_expense_account(company)

	lcv.set(
		"purchase_receipts",
		[
			{
				"receipt_document_type": receipt_document_type,
				"receipt_document": receipt_document,
				"supplier": ref_doc.supplier,
				"posting_date": ref_doc.posting_date,
				"grand_total": ref_doc.base_grand_total,
			}
		],
	)

	lcv.set(
		"taxes",
		[
			{
				"description": "Insurance Charges",
				"expense_account": expense_account,
				"amount": charges,
			}
		],
	)

	lcv.insert()

	distribute_landed_cost_on_items(lcv)

	lcv.submit()

	return lcv


def get_expense_account(company):
	company_abbr = frappe.get_cached_value("Company", company, "abbr")
	return f"Expenses Included In Valuation - {company_abbr}"


def distribute_landed_cost_on_items(lcv):
	based_on = lcv.distribute_charges_based_on.lower()
	total = sum(flt(d.get(based_on)) for d in lcv.get("items"))

	for item in lcv.get("items"):
		item.applicable_charges = flt(item.get(based_on)) * flt(lcv.total_taxes_and_charges) / flt(total)
		item.applicable_charges = flt(item.applicable_charges, lcv.precision("applicable_charges", item))


def ensure_dimension_fields_on_lcv_charges(dimensions):
	"""Create the dimension custom fields the hooks entry and patch add on migrate.

	Test sites are not guaranteed to have migrated since `Landed Cost Taxes and Charges`
	joined `accounting_dimension_doctypes`.
	"""
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		make_dimension_in_accounting_doctypes,
	)

	created = False

	for name in dimensions:
		dimension = frappe.get_doc("Accounting Dimension", name)
		if frappe.db.exists(
			"Custom Field", {"dt": "Landed Cost Taxes and Charges", "fieldname": dimension.fieldname}
		):
			continue

		make_dimension_in_accounting_doctypes(dimension, ["Landed Cost Taxes and Charges"])
		created = True

	if created:
		frappe.clear_cache(doctype="Landed Cost Taxes and Charges")


def create_branch(branch):
	if not frappe.db.exists("Branch", branch):
		frappe.get_doc({"doctype": "Branch", "branch": branch}).insert()

	return branch


class TestLandedCostVoucherAccountingDimensions(ERPNextTestSuite):
	"""Dimensions set on a Landed Cost Voucher charge row must reach the GL entries.

	The charges are posted into the *receipt document's* ledger, and their expense account
	(`Expenses Included In Valuation`) is a Profit and Loss account. A dimension marked
	mandatory for P&L accounts can therefore only be satisfied from the voucher - the
	receipt was submitted before the voucher existed and knows nothing about it.
	"""

	def setUp(self):
		self.company = "_Test Company with perpetual inventory"
		self.warehouse = "Stores - TCP1"
		self.expense_account = get_expense_account(self.company)

		ensure_dimension_fields_on_lcv_charges(["Branch"])
		self.branch_a = create_branch("_Test LCV Branch A")
		self.branch_b = create_branch("_Test LCV Branch B")

	# helpers

	def make_lcv(self, pr, charges, do_not_submit=False):
		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = self.company
		lcv.distribute_charges_based_on = "Amount"
		lcv.set(
			"purchase_receipts",
			[
				{
					"receipt_document_type": "Purchase Receipt",
					"receipt_document": pr.name,
					"supplier": pr.supplier,
					"posting_date": pr.posting_date,
					"grand_total": pr.base_grand_total,
				}
			],
		)

		for idx, charge in enumerate(charges):
			lcv.append(
				"taxes",
				{
					"description": f"_Test Charge {idx + 1}",
					"expense_account": charge.pop("expense_account", self.expense_account),
					**charge,
				},
			)

		lcv.insert()

		if not do_not_submit:
			lcv.submit()

		return lcv

	def get_lcv_gl_entries(self, pr, account=None):
		return frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"is_cancelled": 0,
				**({"account": account} if account else {}),
			},
			fields=["account", "debit", "credit", "cost_center", "project", "branch"],
			order_by="credit desc",
		)

	def make_dimension_mandatory(self, name, mandatory_for_pl=0, mandatory_for_bs=0):
		"""Flag a dimension mandatory for this company, restoring the record afterwards.

		Leaving a dimension mandatory leaks into every later test in the run.
		"""
		dimension = frappe.get_doc("Accounting Dimension", name)
		row = next((d for d in dimension.dimension_defaults if d.company == self.company), None)

		if not row:
			row = dimension.append(
				"dimension_defaults",
				{"company": self.company, "reference_document": dimension.document_type},
			)

		row.mandatory_for_pl = mandatory_for_pl
		row.mandatory_for_bs = mandatory_for_bs
		dimension.save()

	# tests

	def test_charge_row_dimension_reaches_gl_entry(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_lcv(pr, [{"amount": 100, "branch": self.branch_a}])

		charge_entries = self.get_lcv_gl_entries(pr, self.expense_account)
		self.assertEqual(len(charge_entries), 1)
		self.assertEqual(charge_entries[0].credit, 100.0)
		self.assertEqual(charge_entries[0].branch, self.branch_a)

		# the stock leg is untouched - it keeps the receipt item's dimensions
		stock_account = get_inventory_account(self.company, self.warehouse)
		self.assertFalse(self.get_lcv_gl_entries(pr, stock_account)[0].branch)

	def test_charge_row_cost_center_and_project_override_receipt_item(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		create_cost_center(
			cost_center_name="_Test LCV Cost Center",
			company=self.company,
			parent_cost_center=f"{self.company} - TCP1",
		)
		cost_center = "_Test LCV Cost Center - TCP1"

		if not frappe.db.exists("Project", {"project_name": "_Test LCV Project"}):
			frappe.get_doc(
				{"doctype": "Project", "project_name": "_Test LCV Project", "company": self.company}
			).insert()
		project = frappe.db.get_value("Project", {"project_name": "_Test LCV Project"})

		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		item_cost_center = pr.items[0].cost_center

		self.make_lcv(pr, [{"amount": 100, "cost_center": cost_center, "project": project}])

		charge_entries = self.get_lcv_gl_entries(pr, self.expense_account)
		self.assertEqual(len(charge_entries), 1)
		self.assertEqual(charge_entries[0].cost_center, cost_center)
		self.assertEqual(charge_entries[0].project, project)

		# the stock leg still uses the receipt item's cost center
		stock_account = get_inventory_account(self.company, self.warehouse)
		self.assertEqual(self.get_lcv_gl_entries(pr, stock_account)[0].cost_center, item_cost_center)

	def test_blank_charge_row_falls_back_to_receipt_item(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_lcv(pr, [{"amount": 100}])

		charge_entries = self.get_lcv_gl_entries(pr, self.expense_account)
		self.assertEqual(len(charge_entries), 1)
		self.assertEqual(charge_entries[0].cost_center, pr.items[0].cost_center)
		self.assertFalse(charge_entries[0].branch)

	def test_charge_rows_on_same_account_with_different_dimensions_stay_separate(self):
		"""Two charges on one account used to merge, keeping only the first row's dimensions."""
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_lcv(
			pr,
			[
				{"amount": 60, "branch": self.branch_a},
				{"amount": 40, "branch": self.branch_b},
			],
		)

		charge_entries = self.get_lcv_gl_entries(pr, self.expense_account)
		self.assertEqual(len(charge_entries), 2)
		self.assertEqual(
			{(e.branch, e.credit) for e in charge_entries},
			{(self.branch_a, 60.0), (self.branch_b, 40.0)},
		)
		self.assertEqual(sum(e.credit for e in charge_entries), 100.0)

	def test_two_vouchers_on_same_account_with_different_dimensions_stay_separate(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_lcv(pr, [{"amount": 60, "branch": self.branch_a}])
		self.make_lcv(pr, [{"amount": 40, "branch": self.branch_b}])

		charge_entries = self.get_lcv_gl_entries(pr, self.expense_account)
		self.assertEqual(len(charge_entries), 2)
		self.assertEqual(
			{(e.branch, e.credit) for e in charge_entries},
			{(self.branch_a, 60.0), (self.branch_b, 40.0)},
		)

	def test_mandatory_pl_dimension_is_satisfied_by_charge_row(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_dimension_mandatory("Branch", mandatory_for_pl=1)

		self.make_lcv(pr, [{"amount": 100, "branch": self.branch_a}])

		charge_entries = self.get_lcv_gl_entries(pr, self.expense_account)
		self.assertEqual(len(charge_entries), 1)
		self.assertEqual(charge_entries[0].branch, self.branch_a)

	def test_missing_mandatory_dimension_is_reported_on_the_voucher(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_dimension_mandatory("Branch", mandatory_for_pl=1)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_lcv(pr, [{"amount": 100}])

		message = str(raised.exception)
		self.assertIn("Branch", message)
		self.assertIn(self.expense_account, message)

	def test_dimensions_survive_reposting(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		self.make_lcv(
			pr,
			[
				{"amount": 60, "branch": self.branch_a},
				{"amount": 40, "branch": self.branch_b},
			],
		)

		before = {(e.branch, e.credit) for e in self.get_lcv_gl_entries(pr, self.expense_account)}

		items, warehouses = pr.get_items_and_warehouses()
		update_gl_entries_after(pr.posting_date, pr.posting_time, warehouses, items, company=pr.company)

		after = {(e.branch, e.credit) for e in self.get_lcv_gl_entries(pr, self.expense_account)}
		self.assertEqual(before, after)

	def test_cancelling_the_voucher_nets_each_dimension_to_zero(self):
		pr = make_purchase_receipt(company=self.company, warehouse=self.warehouse)
		lcv = self.make_lcv(
			pr,
			[
				{"amount": 60, "branch": self.branch_a},
				{"amount": 40, "branch": self.branch_b},
			],
		)

		lcv.reload()
		lcv.cancel()

		balances = {}
		for entry in frappe.get_all(
			"GL Entry",
			filters={"voucher_no": pr.name, "account": self.expense_account},
			fields=["branch", "debit", "credit"],
		):
			balances[entry.branch] = balances.get(entry.branch, 0.0) + entry.debit - entry.credit

		for branch, balance in balances.items():
			self.assertEqual(flt(balance, 2), 0.0, msg=f"branch {branch} does not net to zero")
