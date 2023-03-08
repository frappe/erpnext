# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, flt, now

from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import update_gl_entries_after
from erpnext.assets.doctype.asset.test_asset import create_asset_category, create_fixed_asset_item
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	get_gl_entries,
	make_purchase_receipt,
)


class TestLandedCostVoucher(FrappeTestCase):
	def test_landed_cost_voucher(self):
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)

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

		self.assertEqual(
			last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction
		)
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

		self.assertEqual(
			last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction
		)
		self.assertEqual(last_sle_after_landed_cost.stock_value - last_sle.stock_value, 50.0)

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

		self.assertEqual(
			last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction
		)

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
		frappe.db.sql(
			"delete from `tabSerial No` where name in ('SN001', 'SN002', 'SN003', 'SN004', 'SN005')"
		)
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			get_multiple_items=True,
			get_taxes_and_charges=True,
			do_not_submit=True,
		)

		pr.items[0].item_code = "_Test Serialized Item"
		pr.items[0].serial_no = "SN001\nSN002\nSN003\nSN004\nSN005"
		pr.submit()

		serial_no_rate = frappe.db.get_value("Serial No", "SN001", "purchase_rate")

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company)

		serial_no = frappe.db.get_value("Serial No", "SN001", ["warehouse", "purchase_rate"], as_dict=1)

		self.assertEqual(serial_no.purchase_rate - serial_no_rate, 5.0)
		self.assertEqual(serial_no.warehouse, "Stores - TCP1")

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

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse=warehouse,
			qty=1,
			rate=200,
			item_code=item_code,
			serial_no=serial_no,
		)

		serial_no_rate = frappe.db.get_value("Serial No", serial_no, "purchase_rate")

		# deliver it before creating LCV
		dn = create_delivery_note(
			item_code=item_code,
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			serial_no=serial_no,
			qty=1,
			rate=500,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
		)

		charges = 10
		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company, charges=charges)

		new_purchase_rate = serial_no_rate + charges

		serial_no = frappe.db.get_value(
			"Serial No", serial_no, ["warehouse", "purchase_rate"], as_dict=1
		)

		self.assertEqual(serial_no.purchase_rate, new_purchase_rate)

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
		for x in range(2):
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
		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import (
			save_new_records,
			test_records,
		)

		save_new_records(test_records)

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
		"Check if LCV for an Asset updates the Assets Gross Purchase Amount correctly."
		frappe.db.set_value(
			"Company", "_Test Company", "capital_work_in_progress_account", "CWIP Account - _TC"
		)

		if not frappe.db.exists("Asset Category", "Computers"):
			create_asset_category()

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
		self.assertEqual(frappe.db.get_value("Asset", assets[0].name, "gross_purchase_amount"), 50080)

		# tear down
		lcv.cancel()
		pr.cancel()


def make_landed_cost_voucher(**args):
	args = frappe._dict(args)
	ref_doc = frappe.get_doc(args.receipt_document_type, args.receipt_document)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = args.company or "_Test Company"
	lcv.distribute_charges_based_on = args.distribute_charges_based_on or "Amount"

	lcv.set(
		"purchase_receipts",
		[
			{
				"receipt_document_type": args.receipt_document_type,
				"receipt_document": args.receipt_document,
				"supplier": ref_doc.supplier,
				"posting_date": ref_doc.posting_date,
				"grand_total": ref_doc.grand_total,
			}
		],
	)

	lcv.set(
		"taxes",
		[
			{
				"description": "Shipping Charges",
				"expense_account": args.expense_account or "Expenses Included In Valuation - TCP1",
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
				"expense_account": "Expenses Included In Valuation - TCP1",
				"amount": charges,
			}
		],
	)

	lcv.insert()

	distribute_landed_cost_on_items(lcv)

	lcv.submit()

	return lcv


def distribute_landed_cost_on_items(lcv):
	based_on = lcv.distribute_charges_based_on.lower()
	total = sum(flt(d.get(based_on)) for d in lcv.get("items"))

	for item in lcv.get("items"):
		item.applicable_charges = flt(item.get(based_on)) * flt(lcv.total_taxes_and_charges) / flt(total)
		item.applicable_charges = flt(item.applicable_charges, lcv.precision("applicable_charges", item))


test_records = frappe.get_test_records("Landed Cost Voucher")
