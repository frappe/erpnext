# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
import json

import frappe
from frappe import qb
from frappe.model.dynamic_links import get_dynamic_link_map
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, format_date, getdate, nowdate, today

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import WarehouseMissingError
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	unlink_payment_on_cancel_of_invoice,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction
from erpnext.accounts.utils import PaymentEntryUnlinkError
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import create_asset, create_asset_data
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
)
from erpnext.controllers.accounts_controller import update_invoice_status
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data
from erpnext.exceptions import InvalidAccountCurrency, InvalidCurrency
from erpnext.selling.doctype.customer.test_customer import get_customer_dict
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.stock_entry.test_stock_entry import (
	get_qty_after_transaction,
	make_stock_entry,
)
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.utils import get_incoming_rate, get_stock_balance


class TestSalesInvoice(FrappeTestCase):
	def setUp(self):
		from erpnext.stock.doctype.stock_ledger_entry.test_stock_ledger_entry import create_items

		create_items(["_Test Internal Transfer Item"], uoms=[{"uom": "Box", "conversion_factor": 10}])
		create_internal_parties()
		setup_accounts()
		frappe.db.set_single_value("Accounts Settings", "acc_frozen_upto", None)

	def tearDown(self):
		frappe.db.rollback()

	def make(self):
		w = frappe.copy_doc(test_records[0])
		w.is_pos = 0
		w.insert()
		w.submit()
		return w

	@classmethod
	def setUpClass(self):
		unlink_payment_on_cancel_of_invoice()

	@classmethod
	def tearDownClass(self):
		unlink_payment_on_cancel_of_invoice(0)

	def test_timestamp_change(self):
		w = frappe.copy_doc(test_records[0])
		w.docstatus = 0
		w.insert()

		w2 = frappe.get_doc(w.doctype, w.name)

		import time

		time.sleep(1)
		w.save()

		import time

		time.sleep(1)
		self.assertRaises(frappe.TimestampMismatchError, w2.save)

	def test_sales_invoice_change_naming_series(self):
		si = frappe.copy_doc(test_records[2])
		si.insert()
		si.naming_series = "TEST-"

		self.assertRaises(frappe.CannotChangeConstantError, si.save)

		si = frappe.copy_doc(test_records[1])
		si.insert()
		si.naming_series = "TEST-"

		self.assertRaises(frappe.CannotChangeConstantError, si.save)

	def test_add_terms_after_save(self):
		si = frappe.copy_doc(test_records[2])
		si.insert()

		self.assertTrue(si.payment_schedule)
		self.assertEqual(getdate(si.payment_schedule[0].due_date), getdate(si.due_date))

	def test_sales_invoice_calculation_base_currency(self):
		si = frappe.copy_doc(test_records[2])
		si.insert()

		expected_values = {
			"keys": [
				"price_list_rate",
				"discount_percentage",
				"rate",
				"amount",
				"base_price_list_rate",
				"base_rate",
				"base_amount",
			],
			"_Test Item Home Desktop 100": [50, 0, 50, 500, 50, 50, 500],
			"_Test Item Home Desktop 200": [150, 0, 150, 750, 150, 150, 750],
		}

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values) - 1)

		# check if item values are calculated
		for d in si.get("items"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEqual(si.base_net_total, 1250)
		self.assertEqual(si.net_total, 1250)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Shipping Charges - _TC": [100, 1350],
			"_Test Account Customs Duty - _TC": [125, 1475],
			"_Test Account Excise Duty - _TC": [140, 1615],
			"_Test Account Education Cess - _TC": [2.8, 1617.8],
			"_Test Account S&H Education Cess - _TC": [1.4, 1619.2],
			"_Test Account CST - _TC": [32.38, 1651.58],
			"_Test Account VAT - _TC": [156.25, 1807.83],
			"_Test Account Discount - _TC": [-180.78, 1627.05],
		}

		for d in si.get("taxes"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.account_head][i])

		self.assertEqual(si.base_grand_total, 1627.05)
		self.assertEqual(si.grand_total, 1627.05)

	def test_payment_entry_unlink_against_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		si = frappe.copy_doc(test_records[0])
		si.is_pos = 0
		si.insert()
		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = si.currency
		pe.paid_to_account_currency = si.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = si.outstanding_amount
		pe.insert()
		pe.submit()

		unlink_payment_on_cancel_of_invoice(0)
		si = frappe.get_doc("Sales Invoice", si.name)
		self.assertRaises(frappe.LinkExistsError, si.cancel)
		unlink_payment_on_cancel_of_invoice()

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_payment_entry_unlink_against_standalone_credit_note(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		si1 = create_sales_invoice(rate=1000)
		si2 = create_sales_invoice(rate=300)
		si3 = create_sales_invoice(qty=-1, rate=300, is_return=1)

		pe = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Bank - _TC")
		pe.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": si2.name,
				"total_amount": si2.grand_total,
				"outstanding_amount": si2.outstanding_amount,
				"allocated_amount": si2.outstanding_amount,
			},
		)

		pe.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": si3.name,
				"total_amount": si3.grand_total,
				"outstanding_amount": si3.outstanding_amount,
				"allocated_amount": si3.outstanding_amount,
			},
		)

		pe.reference_no = "Test001"
		pe.reference_date = nowdate()
		pe.save()
		pe.submit()

		si2.load_from_db()
		si2.cancel()

		si1.load_from_db()
		self.assertRaises(PaymentEntryUnlinkError, si1.cancel)

	def test_sales_invoice_calculation_export_currency(self):
		si = frappe.copy_doc(test_records[2])
		si.currency = "USD"
		si.conversion_rate = 50
		si.get("items")[0].rate = 1
		si.get("items")[0].price_list_rate = 1
		si.get("items")[1].rate = 3
		si.get("items")[1].price_list_rate = 3

		# change shipping to $2
		si.get("taxes")[0].tax_amount = 2
		si.insert()

		expected_values = {
			"keys": [
				"price_list_rate",
				"discount_percentage",
				"rate",
				"amount",
				"base_price_list_rate",
				"base_rate",
				"base_amount",
			],
			"_Test Item Home Desktop 100": [1, 0, 1, 10, 50, 50, 500],
			"_Test Item Home Desktop 200": [3, 0, 3, 15, 150, 150, 750],
		}

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values) - 1)

		# check if item values are calculated
		for d in si.get("items"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEqual(si.total, 25)
		self.assertEqual(si.base_total, 1250)
		self.assertEqual(si.net_total, 25)
		self.assertEqual(si.base_net_total, 1250)

		# check tax calculation
		expected_values = {
			"keys": ["base_tax_amount", "base_total", "tax_amount", "total"],
			"_Test Account Shipping Charges - _TC": [100, 1350, 2, 27],
			"_Test Account Customs Duty - _TC": [125, 1475, 2.5, 29.5],
			"_Test Account Excise Duty - _TC": [140, 1615, 2.8, 32.3],
			"_Test Account Education Cess - _TC": [3, 1618, 0.06, 32.36],
			"_Test Account S&H Education Cess - _TC": [1.5, 1619.5, 0.03, 32.39],
			"_Test Account CST - _TC": [32.5, 1652, 0.65, 33.04],
			"_Test Account VAT - _TC": [156.0, 1808.0, 3.12, 36.16],
			"_Test Account Discount - _TC": [-181.0, 1627.0, -3.62, 32.54],
		}

		for d in si.get("taxes"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.account_head][i])

		self.assertEqual(si.base_grand_total, 1627.0)
		self.assertEqual(si.grand_total, 32.54)

	def test_sales_invoice_with_discount_and_inclusive_tax(self):
		si = create_sales_invoice(qty=100, rate=50, do_not_save=True)
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 14,
				"included_in_print_rate": 1,
			},
		)
		si.append(
			"taxes",
			{
				"charge_type": "On Item Quantity",
				"account_head": "_Test Account Education Cess - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "CESS",
				"rate": 5,
				"included_in_print_rate": 1,
			},
		)
		si.insert()

		# with inclusive tax
		self.assertEqual(si.items[0].net_amount, 3947.368421052631)
		self.assertEqual(si.net_total, 3947.37)
		self.assertEqual(si.grand_total, 5000)

		si.reload()

		# additional discount
		si.discount_amount = 100
		si.apply_discount_on = "Net Total"
		si.payment_schedule = []

		si.save()

		# with inclusive tax and additional discount
		self.assertEqual(si.net_total, 3847.37)
		self.assertEqual(si.grand_total, 4886)

		si.reload()

		# additional discount on grand total
		si.discount_amount = 100
		si.apply_discount_on = "Grand Total"
		si.payment_schedule = []

		si.save()

		# with inclusive tax and additional discount
		self.assertEqual(si.net_total, 3859.65)
		self.assertEqual(si.grand_total, 4900.00)

	def test_sales_invoice_discount_amount(self):
		si = frappe.copy_doc(test_records[3])
		si.discount_amount = 104.94
		si.append(
			"taxes",
			{
				"charge_type": "On Previous Row Amount",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 10,
				"row_id": 8,
			},
		)
		si.insert()

		expected_values = [
			{
				"item_code": "_Test Item Home Desktop 100",
				"price_list_rate": 62.5,
				"discount_percentage": 0,
				"rate": 62.5,
				"amount": 625,
				"base_price_list_rate": 62.5,
				"base_rate": 62.5,
				"base_amount": 625,
				"net_rate": 46.54,
				"net_amount": 465.37,
				"base_net_rate": 46.54,
				"base_net_amount": 465.37,
			},
			{
				"item_code": "_Test Item Home Desktop 200",
				"price_list_rate": 190.66,
				"discount_percentage": 0,
				"rate": 190.66,
				"amount": 953.3,
				"base_price_list_rate": 190.66,
				"base_rate": 190.66,
				"base_amount": 953.3,
				"net_rate": 139.62,
				"net_amount": 698.08,
				"base_net_rate": 139.62,
				"base_net_amount": 698.08,
			},
		]

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values))

		# check if item values are calculated
		for i, d in enumerate(si.get("items")):
			for k, v in expected_values[i].items():
				self.assertEqual(d.get(k), v)

		# check net total
		self.assertEqual(si.base_net_total, 1163.45)
		self.assertEqual(si.total, 1578.3)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "tax_amount_after_discount_amount", "total"],
			"_Test Account Excise Duty - _TC": [140, 130.31, 1293.76],
			"_Test Account Education Cess - _TC": [2.8, 2.61, 1296.37],
			"_Test Account S&H Education Cess - _TC": [1.4, 1.30, 1297.67],
			"_Test Account CST - _TC": [27.88, 25.95, 1323.62],
			"_Test Account VAT - _TC": [156.25, 145.43, 1469.05],
			"_Test Account Customs Duty - _TC": [125, 116.34, 1585.39],
			"_Test Account Shipping Charges - _TC": [100, 100, 1685.39],
			"_Test Account Discount - _TC": [-180.33, -168.54, 1516.85],
			"_Test Account Service Tax - _TC": [-18.03, -16.85, 1500.00],
		}

		for d in si.get("taxes"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.account_head][i])

		self.assertEqual(si.base_grand_total, 1500)
		self.assertEqual(si.grand_total, 1500)
		self.assertEqual(si.rounding_adjustment, 0.0)

	def test_discount_amount_gl_entry(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "Round Off - _TC")
		si = frappe.copy_doc(test_records[3])
		si.discount_amount = 104.94
		si.append(
			"taxes",
			{
				"doctype": "Sales Taxes and Charges",
				"charge_type": "On Previous Row Amount",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 10,
				"row_id": 8,
			},
		)
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = dict(
			(d[0], d)
			for d in [
				[si.debit_to, 1500, 0.0],
				[test_records[3]["items"][0]["income_account"], 0.0, 1163.45],
				[test_records[3]["taxes"][0]["account_head"], 0.0, 130.31],
				[test_records[3]["taxes"][1]["account_head"], 0.0, 2.61],
				[test_records[3]["taxes"][2]["account_head"], 0.0, 1.30],
				[test_records[3]["taxes"][3]["account_head"], 0.0, 25.95],
				[test_records[3]["taxes"][4]["account_head"], 0.0, 145.43],
				[test_records[3]["taxes"][5]["account_head"], 0.0, 116.34],
				[test_records[3]["taxes"][6]["account_head"], 0.0, 100],
				[test_records[3]["taxes"][7]["account_head"], 168.54, 0.0],
				["_Test Account Service Tax - _TC", 16.85, 0.0],
				["Round Off - _TC", 0.01, 0.0],
			]
		)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

		# cancel
		si.cancel()

		gle = frappe.db.sql(
			"""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			si.name,
		)

		self.assertTrue(gle)

	def test_tax_calculation_with_multiple_items(self):
		si = create_sales_invoice(qty=84, rate=4.6, do_not_save=True)
		item_row = si.get("items")[0]
		for qty in (54, 288, 144, 430):
			item_row_copy = copy.deepcopy(item_row)
			item_row_copy.qty = qty
			si.append("items", item_row_copy)

		si.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 19,
			},
		)
		si.insert()

		self.assertEqual(si.net_total, 4600)

		self.assertEqual(si.get("taxes")[0].tax_amount, 874.0)
		self.assertEqual(si.get("taxes")[0].total, 5474.0)

		self.assertEqual(si.grand_total, 5474.0)

	def test_tax_calculation_with_item_tax_template(self):
		si = create_sales_invoice(qty=84, rate=4.6, do_not_save=True)
		item_row = si.get("items")[0]

		add_items = [
			(54, "_Test Account Excise Duty @ 12 - _TC"),
			(288, "_Test Account Excise Duty @ 15 - _TC"),
			(144, "_Test Account Excise Duty @ 20 - _TC"),
			(430, "_Test Item Tax Template 1 - _TC"),
		]
		for qty, item_tax_template in add_items:
			item_row_copy = copy.deepcopy(item_row)
			item_row_copy.qty = qty
			item_row_copy.item_tax_template = item_tax_template
			si.append("items", item_row_copy)

		si.append(
			"taxes",
			{
				"account_head": "_Test Account Excise Duty - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Excise Duty",
				"doctype": "Sales Taxes and Charges",
				"rate": 11,
			},
		)
		si.append(
			"taxes",
			{
				"account_head": "_Test Account Education Cess - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Education Cess",
				"doctype": "Sales Taxes and Charges",
				"rate": 0,
			},
		)
		si.append(
			"taxes",
			{
				"account_head": "_Test Account S&H Education Cess - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "S&H Education Cess",
				"doctype": "Sales Taxes and Charges",
				"rate": 3,
			},
		)
		si.insert()

		self.assertEqual(si.net_total, 4600)

		self.assertEqual(si.get("taxes")[0].tax_amount, 502.41)
		self.assertEqual(si.get("taxes")[0].total, 5102.41)

		self.assertEqual(si.get("taxes")[1].tax_amount, 197.80)
		self.assertEqual(si.get("taxes")[1].total, 5300.21)

		self.assertEqual(si.get("taxes")[2].tax_amount, 375.36)
		self.assertEqual(si.get("taxes")[2].total, 5675.57)

		self.assertEqual(si.grand_total, 5675.57)
		self.assertEqual(si.rounding_adjustment, 0.43)
		self.assertEqual(si.rounded_total, 5676.0)

	def test_tax_calculation_with_multiple_items_and_discount(self):
		si = create_sales_invoice(qty=1, rate=75, do_not_save=True)
		item_row = si.get("items")[0]
		for rate in (500, 200, 100, 50, 50):
			item_row_copy = copy.deepcopy(item_row)
			item_row_copy.price_list_rate = rate
			item_row_copy.rate = rate
			si.append("items", item_row_copy)

		si.apply_discount_on = "Net Total"
		si.discount_amount = 75.0

		si.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 24,
			},
		)
		si.insert()

		self.assertEqual(si.total, 975)
		self.assertEqual(si.net_total, 900)

		self.assertEqual(si.get("taxes")[0].tax_amount, 216.0)
		self.assertEqual(si.get("taxes")[0].total, 1116.0)

		self.assertEqual(si.grand_total, 1116.0)

	def test_inclusive_rate_validations(self):
		si = frappe.copy_doc(test_records[2])
		for i, tax in enumerate(si.get("taxes")):
			tax.idx = i + 1

		si.get("items")[0].price_list_rate = 62.5
		si.get("items")[0].price_list_rate = 191
		for i in range(6):
			si.get("taxes")[i].included_in_print_rate = 1

		# tax type "Actual" cannot be inclusive
		self.assertRaises(frappe.ValidationError, si.insert)

		# taxes above included type 'On Previous Row Total' should also be included
		si.get("taxes")[0].included_in_print_rate = 0
		self.assertRaises(frappe.ValidationError, si.insert)

	def test_sales_invoice_calculation_base_currency_with_tax_inclusive_price(self):
		# prepare
		si = frappe.copy_doc(test_records[3])
		si.insert()

		expected_values = {
			"keys": [
				"price_list_rate",
				"discount_percentage",
				"rate",
				"amount",
				"base_price_list_rate",
				"base_rate",
				"base_amount",
				"net_rate",
				"net_amount",
			],
			"_Test Item Home Desktop 100": [
				62.5,
				0,
				62.5,
				625.0,
				62.5,
				62.5,
				625.0,
				50,
				499.97600115194473,
			],
			"_Test Item Home Desktop 200": [
				190.66,
				0,
				190.66,
				953.3,
				190.66,
				190.66,
				953.3,
				150,
				749.9968530500239,
			],
		}

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values) - 1)

		# check if item values are calculated
		for d in si.get("items"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEqual(si.net_total, 1249.97)
		self.assertEqual(si.total, 1578.3)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Excise Duty - _TC": [140, 1389.97],
			"_Test Account Education Cess - _TC": [2.8, 1392.77],
			"_Test Account S&H Education Cess - _TC": [1.4, 1394.17],
			"_Test Account CST - _TC": [27.88, 1422.05],
			"_Test Account VAT - _TC": [156.25, 1578.30],
			"_Test Account Customs Duty - _TC": [125, 1703.30],
			"_Test Account Shipping Charges - _TC": [100, 1803.30],
			"_Test Account Discount - _TC": [-180.33, 1622.97],
		}

		for d in si.get("taxes"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.account_head][i])

		self.assertEqual(si.base_grand_total, 1622.97)
		self.assertEqual(si.grand_total, 1622.97)

	def test_sales_invoice_calculation_export_currency_with_tax_inclusive_price(self):
		# prepare
		si = frappe.copy_doc(test_records[3])
		si.currency = "USD"
		si.conversion_rate = 50
		si.get("items")[0].price_list_rate = 55.56
		si.get("items")[0].discount_percentage = 10
		si.get("items")[1].price_list_rate = 187.5
		si.get("items")[1].discount_percentage = 20

		# change shipping to $2
		si.get("taxes")[6].tax_amount = 2

		si.insert()

		expected_values = [
			{
				"item_code": "_Test Item Home Desktop 100",
				"price_list_rate": 55.56,
				"discount_percentage": 10,
				"rate": 50,
				"amount": 500,
				"base_price_list_rate": 2778,
				"base_rate": 2500,
				"base_amount": 25000,
				"net_rate": 40,
				"net_amount": 399.9808009215558,
				"base_net_rate": 2000,
				"base_net_amount": 19999,
			},
			{
				"item_code": "_Test Item Home Desktop 200",
				"price_list_rate": 187.5,
				"discount_percentage": 20,
				"rate": 150,
				"amount": 750,
				"base_price_list_rate": 9375,
				"base_rate": 7500,
				"base_amount": 37500,
				"net_rate": 118.01,
				"net_amount": 590.0531205155963,
				"base_net_rate": 5900.5,
				"base_net_amount": 29502.5,
			},
		]

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values))

		# check if item values are calculated
		for i, d in enumerate(si.get("items")):
			for key, val in expected_values[i].items():
				self.assertEqual(d.get(key), val)

		# check net total
		self.assertEqual(si.base_net_total, 49501.5)
		self.assertEqual(si.net_total, 990.03)
		self.assertEqual(si.total, 1250)

		# check tax calculation
		expected_values = {
			"keys": ["base_tax_amount", "base_total", "tax_amount", "total"],
			"_Test Account Excise Duty - _TC": [5540.0, 55041.5, 110.80, 1100.83],
			"_Test Account Education Cess - _TC": [111, 55152.5, 2.22, 1103.05],
			"_Test Account S&H Education Cess - _TC": [55.5, 55208.0, 1.11, 1104.16],
			"_Test Account CST - _TC": [1104, 56312.0, 22.08, 1126.24],
			"_Test Account VAT - _TC": [6187.5, 62499.5, 123.75, 1249.99],
			"_Test Account Customs Duty - _TC": [4950.0, 67449.5, 99.0, 1348.99],
			"_Test Account Shipping Charges - _TC": [100, 67549.5, 2, 1350.99],
			"_Test Account Discount - _TC": [-6755, 60794.5, -135.10, 1215.89],
		}

		for d in si.get("taxes"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.account_head][i])

		self.assertEqual(si.base_grand_total, 60795)
		self.assertEqual(si.grand_total, 1215.90)
		self.assertEqual(si.rounding_adjustment, 0.01)
		self.assertEqual(si.base_rounding_adjustment, 0.50)

	def test_outstanding(self):
		w = self.make()
		self.assertEqual(w.outstanding_amount, w.base_rounded_total)

	def test_rounded_total_with_cash_discount(self):
		si = frappe.copy_doc(test_records[2])

		item = copy.deepcopy(si.get("items")[0])
		item.update(
			{
				"qty": 1,
				"rate": 14960.66,
			}
		)

		si.set("items", [item])
		si.set("taxes", [])
		si.apply_discount_on = "Grand Total"
		si.is_cash_or_non_trade_discount = 1
		si.discount_amount = 1
		si.insert()

		self.assertEqual(si.grand_total, 14959.66)
		self.assertEqual(si.rounded_total, 14960)
		self.assertEqual(si.rounding_adjustment, 0.34)

	def test_payment(self):
		w = self.make()

		from erpnext.accounts.doctype.journal_entry.test_journal_entry import (
			test_records as jv_test_records,
		)

		jv = frappe.get_doc(frappe.copy_doc(jv_test_records[0]))
		jv.get("accounts")[0].reference_type = w.doctype
		jv.get("accounts")[0].reference_name = w.name
		jv.insert()
		jv.submit()

		self.assertEqual(frappe.db.get_value("Sales Invoice", w.name, "outstanding_amount"), 162.0)

		link_data = get_dynamic_link_map().get("Sales Invoice", [])
		link_doctypes = [d.parent for d in link_data]

		# test case for dynamic link order
		self.assertTrue(link_doctypes.index("GL Entry") > link_doctypes.index("Journal Entry Account"))

		jv.cancel()
		self.assertEqual(frappe.db.get_value("Sales Invoice", w.name, "outstanding_amount"), 562.0)

	def test_outstanding_on_cost_center_allocation(self):
		# setup cost centers
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.cost_center_allocation.test_cost_center_allocation import (
			create_cost_center_allocation,
		)

		cost_centers = [
			"Main Cost Center 1",
			"Sub Cost Center 1",
			"Sub Cost Center 2",
		]
		for cc in cost_centers:
			create_cost_center(cost_center_name=cc, company="_Test Company")

		cca = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 60, "Sub Cost Center 2 - _TC": 40},
		)

		# make invoice
		si = frappe.copy_doc(test_records[0])
		si.is_pos = 0
		si.insert()
		si.submit()

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		# make payment - fully paid
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = si.currency
		pe.paid_to_account_currency = si.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = si.outstanding_amount
		pe.cost_center = cca.main_cost_center
		pe.insert()
		pe.submit()

		# cancel cost center allocation
		cca.cancel()

		si.reload()
		self.assertEqual(si.outstanding_amount, 0)

	def test_sales_invoice_gl_entry_without_perpetual_inventory(self):
		si = frappe.copy_doc(test_records[1])
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = dict(
			(d[0], d)
			for d in [
				[si.debit_to, 630.0, 0.0],
				[test_records[1]["items"][0]["income_account"], 0.0, 500.0],
				[test_records[1]["taxes"][0]["account_head"], 0.0, 80.0],
				[test_records[1]["taxes"][1]["account_head"], 0.0, 50.0],
			]
		)

		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

		# cancel
		si.cancel()

		gle = frappe.db.sql(
			"""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			si.name,
		)

		self.assertTrue(gle)

	def test_pos_gl_entry_with_perpetual_inventory(self):
		make_pos_profile(
			company="_Test Company with perpetual inventory",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			write_off_account="_Test Write Off - TCP1",
		)

		make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
		)

		pos = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			do_not_save=True,
		)

		pos.is_pos = 1
		pos.update_stock = 1

		pos.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - TCP1", "amount": 50}
		)
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - TCP1", "amount": 50})

		taxes = get_taxes_and_charges()
		pos.taxes = []
		for tax in taxes:
			pos.append("taxes", tax)

		si = frappe.copy_doc(pos)
		si.insert()
		si.submit()
		self.assertEqual(si.paid_amount, 100.0)

		self.validate_pos_gl_entry(si, pos, 50)

	def test_pos_returns_with_repayment(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		pos_profile = make_pos_profile()

		pos_profile.payments = []
		pos_profile.append("payments", {"default": 1, "mode_of_payment": "Cash"})

		pos_profile.save()

		pos = create_sales_invoice(qty=10, do_not_save=True)

		pos.is_pos = 1
		pos.pos_profile = pos_profile.name

		pos.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - _TC", "amount": 500}
		)
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 500})
		pos.insert()
		pos.submit()

		pos_return = make_sales_return(pos.name)

		pos_return.insert()
		pos_return.submit()

		self.assertEqual(pos_return.get("payments")[0].amount, -500)
		self.assertEqual(pos_return.get("payments")[1].amount, -500)

	def test_pos_change_amount(self):
		make_pos_profile(
			company="_Test Company with perpetual inventory",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			write_off_account="_Test Write Off - TCP1",
		)

		make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
		)

		pos = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			do_not_save=True,
		)

		pos.is_pos = 1
		pos.update_stock = 1

		pos.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - TCP1", "amount": 50}
		)
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - TCP1", "amount": 60})

		pos.write_off_outstanding_amount_automatically = 1
		pos.insert()
		pos.submit()

		self.assertEqual(pos.grand_total, 100.0)
		self.assertEqual(pos.write_off_amount, 0)

	def test_auto_write_off_amount(self):
		make_pos_profile(
			company="_Test Company with perpetual inventory",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			write_off_account="_Test Write Off - TCP1",
		)

		make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
		)

		pos = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			do_not_save=True,
		)

		pos.is_pos = 1
		pos.update_stock = 1

		pos.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - TCP1", "amount": 50}
		)
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - TCP1", "amount": 40})

		pos.write_off_outstanding_amount_automatically = 1
		pos.insert()
		pos.submit()

		self.assertEqual(pos.grand_total, 100.0)
		self.assertEqual(pos.write_off_amount, 10)

	def test_ledger_entries_of_return_pos_invoice(self):
		make_pos_profile()

		pos = create_sales_invoice(do_not_save=True)
		pos.is_pos = 1
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
		pos.save().submit()
		self.assertEqual(pos.outstanding_amount, 0.0)
		self.assertEqual(pos.status, "Paid")

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		pos_return = make_sales_return(pos.name)
		pos_return.save().submit()
		pos_return.reload()
		pos.reload()
		self.assertEqual(pos_return.is_return, 1)
		self.assertEqual(pos_return.return_against, pos.name)
		self.assertEqual(pos_return.outstanding_amount, 0.0)
		self.assertEqual(pos_return.status, "Return")
		self.assertEqual(pos.outstanding_amount, 0.0)
		self.assertEqual(pos.status, "Credit Note Issued")

		expected = (
			("Cash - _TC", 0.0, 100.0, pos_return.name, None),
			("Debtors - _TC", 0.0, 100.0, pos_return.name, pos_return.name),
			("Debtors - _TC", 100.0, 0.0, pos_return.name, pos_return.name),
			("Sales - _TC", 100.0, 0.0, pos_return.name, None),
		)
		res = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pos_return.name, "is_cancelled": 0},
			fields=["account", "debit", "credit", "voucher_no", "against_voucher"],
			order_by="account, debit, credit",
			as_list=1,
		)
		self.assertEqual(expected, res)

	def test_pos_with_no_gl_entry_for_change_amount(self):
		frappe.db.set_single_value("Accounts Settings", "post_change_gl_entries", 0)

		make_pos_profile(
			company="_Test Company with perpetual inventory",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			write_off_account="_Test Write Off - TCP1",
		)

		make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
		)

		pos = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			item_code="_Test FG Item",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			do_not_save=True,
		)

		pos.is_pos = 1
		pos.update_stock = 1

		taxes = get_taxes_and_charges()
		pos.taxes = []
		for tax in taxes:
			pos.append("taxes", tax)

		pos.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - TCP1", "amount": 50}
		)
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - TCP1", "amount": 60})

		pos.insert()
		pos.submit()

		self.assertEqual(pos.grand_total, 100.0)
		self.assertEqual(pos.change_amount, 10)

		self.validate_pos_gl_entry(pos, pos, 60, validate_without_change_gle=True)

		frappe.db.set_single_value("Accounts Settings", "post_change_gl_entries", 1)

	def validate_pos_gl_entry(self, si, pos, cash_amount, validate_without_change_gle=False):
		if validate_without_change_gle:
			cash_amount -= pos.change_amount

		# check stock ledger entries
		sle = frappe.db.sql(
			"""select * from `tabStock Ledger Entry`
			where voucher_type = 'Sales Invoice' and voucher_no = %s""",
			si.name,
			as_dict=1,
		)[0]
		self.assertTrue(sle)
		self.assertEqual(
			[sle.item_code, sle.warehouse, sle.actual_qty], ["_Test FG Item", "Stores - TCP1", -1.0]
		)

		# check gl entries
		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc, debit asc, credit asc""",
			si.name,
			as_dict=1,
		)
		self.assertTrue(gl_entries)

		stock_in_hand = get_inventory_account("_Test Company with perpetual inventory")
		expected_gl_entries = sorted(
			[
				[si.debit_to, 100.0, 0.0],
				[pos.items[0].income_account, 0.0, 89.09],
				["Round Off - TCP1", 0.0, 0.01],
				[pos.taxes[0].account_head, 0.0, 10.69],
				[pos.taxes[1].account_head, 0.0, 0.21],
				[stock_in_hand, 0.0, abs(sle.stock_value_difference)],
				[pos.items[0].expense_account, abs(sle.stock_value_difference), 0.0],
				[si.debit_to, 0.0, 50.0],
				[si.debit_to, 0.0, cash_amount],
				["_Test Bank - TCP1", 50, 0.0],
				["Cash - TCP1", cash_amount, 0.0],
			]
		)

		for i, gle in enumerate(sorted(gl_entries, key=lambda gle: gle.account)):
			self.assertEqual(expected_gl_entries[i][0], gle.account)
			self.assertEqual(expected_gl_entries[i][1], gle.debit)
			self.assertEqual(expected_gl_entries[i][2], gle.credit)

		si.cancel()
		gle = frappe.db.sql(
			"""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			si.name,
		)

		self.assertTrue(gle)

		frappe.db.sql("delete from `tabPOS Profile`")

	def test_bin_details_of_packed_item(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item

		# test Update Items with product bundle
		if not frappe.db.exists("Item", "_Test Product Bundle Item New"):
			bundle_item = make_item("_Test Product Bundle Item New", {"is_stock_item": 0})
			bundle_item.append(
				"item_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
			)
			bundle_item.save(ignore_permissions=True)

		make_item("_Packed Item New 1", {"is_stock_item": 1})
		make_product_bundle("_Test Product Bundle Item New", ["_Packed Item New 1"], 2)

		si = create_sales_invoice(
			item_code="_Test Product Bundle Item New",
			update_stock=1,
			warehouse="_Test Warehouse - _TC",
			transaction_date=add_days(nowdate(), -1),
			do_not_submit=1,
		)

		make_stock_entry(item="_Packed Item New 1", target="_Test Warehouse - _TC", qty=120, rate=100)

		bin_details = frappe.db.get_value(
			"Bin",
			{"item_code": "_Packed Item New 1", "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "projected_qty", "ordered_qty"],
			as_dict=1,
		)

		si.transaction_date = nowdate()
		si.save()

		packed_item = si.packed_items[0]
		self.assertEqual(flt(bin_details.actual_qty), flt(packed_item.actual_qty))
		self.assertEqual(flt(bin_details.projected_qty), flt(packed_item.projected_qty))
		self.assertEqual(flt(bin_details.ordered_qty), flt(packed_item.ordered_qty))

	def test_pos_si_without_payment(self):
		make_pos_profile()

		pos = copy.deepcopy(test_records[1])
		pos["is_pos"] = 1
		pos["update_stock"] = 1

		si = frappe.copy_doc(pos)
		si.insert()

		# Check that the invoice cannot be submitted without payments
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_sales_invoice_gl_entry_with_perpetual_inventory_no_item_code(self):
		si = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			income_account="Sales - TCP1",
			cost_center="Main - TCP1",
			do_not_save=True,
		)
		si.get("items")[0].item_code = None
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)
		self.assertTrue(gl_entries)

		expected_values = dict(
			(d[0], d) for d in [["Debtors - TCP1", 100.0, 0.0], ["Sales - TCP1", 0.0, 100.0]]
		)
		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def test_sales_invoice_gl_entry_with_perpetual_inventory_non_stock_item(self):
		si = create_sales_invoice(item="_Test Non Stock Item")

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)
		self.assertTrue(gl_entries)

		expected_values = dict(
			(d[0], d)
			for d in [
				[si.debit_to, 100.0, 0.0],
				[test_records[1]["items"][0]["income_account"], 0.0, 100.0],
			]
		)
		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def _insert_purchase_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
			test_records as pr_test_records,
		)

		pr = frappe.copy_doc(pr_test_records[0])
		pr.naming_series = "_T-Purchase Receipt-"
		pr.insert()
		pr.submit()

	def _insert_delivery_note(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import (
			test_records as dn_test_records,
		)

		dn = frappe.copy_doc(dn_test_records[0])
		dn.naming_series = "_T-Delivery Note-"
		dn.insert()
		dn.submit()
		return dn

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_sales_invoice_with_advance(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import (
			test_records as jv_test_records,
		)

		jv = frappe.copy_doc(jv_test_records[0])
		jv.insert()
		jv.submit()

		si = frappe.copy_doc(test_records[0])
		si.allocate_advances_automatically = 0
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": "Journal Entry",
				"reference_name": jv.name,
				"reference_row": jv.get("accounts")[0].name,
				"advance_amount": 400,
				"allocated_amount": 300,
				"remarks": jv.remark,
			},
		)
		si.insert()
		si.submit()
		si.load_from_db()

		self.assertTrue(
			frappe.db.sql(
				"""select name from `tabJournal Entry Account`
			where reference_name=%s""",
				si.name,
			)
		)

		self.assertTrue(
			frappe.db.sql(
				"""select name from `tabJournal Entry Account`
			where reference_name=%s and credit_in_account_currency=300""",
				si.name,
			)
		)

		self.assertEqual(si.outstanding_amount, 262.0)

		si.cancel()

	def test_serialized(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		se = make_serialized_item()
		se.load_from_db()
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)

		si = frappe.copy_doc(test_records[0])
		si.update_stock = 1
		si.get("items")[0].item_code = "_Test Serialized Item With Series"
		si.get("items")[0].qty = 1
		si.get("items")[0].warehouse = se.get("items")[0].t_warehouse
		si.get("items")[0].serial_and_batch_bundle = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": si.get("items")[0].item_code,
					"warehouse": si.get("items")[0].warehouse,
					"company": si.company,
					"qty": 1,
					"voucher_type": "Stock Entry",
					"serial_nos": [serial_nos[0]],
					"posting_date": si.posting_date,
					"posting_time": si.posting_time,
					"type_of_transaction": "Outward",
					"do_not_submit": True,
				}
			)
		).name

		si.insert()
		si.submit()

		self.assertFalse(frappe.db.get_value("Serial No", serial_nos[0], "warehouse"))

		return si

	def test_serialized_cancel(self):
		si = self.test_serialized()
		si.reload()
		serial_nos = get_serial_nos_from_bundle(si.get("items")[0].serial_and_batch_bundle)

		si.cancel()

		self.assertEqual(
			frappe.db.get_value("Serial No", serial_nos[0], "warehouse"), "_Test Warehouse - _TC"
		)

	def test_serial_numbers_against_delivery_note(self):
		"""
		check if the sales invoice item serial numbers and the delivery note items
		serial numbers are same
		"""
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		se = make_serialized_item()
		se.load_from_db()
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0]

		dn = create_delivery_note(item=se.get("items")[0].item_code, serial_no=[serial_nos])
		dn.submit()
		dn.load_from_db()

		serial_nos = get_serial_nos_from_bundle(dn.get("items")[0].serial_and_batch_bundle)[0]
		self.assertTrue(get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0])

		si = make_sales_invoice(dn.name)
		si.save()

	def test_return_sales_invoice(self):
		make_stock_entry(item_code="_Test Item", target="Stores - TCP1", qty=50, basic_rate=100)

		actual_qty_0 = get_qty_after_transaction(item_code="_Test Item", warehouse="Stores - TCP1")

		si = create_sales_invoice(
			qty=5,
			rate=500,
			update_stock=1,
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			item_code="_Test Item",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		actual_qty_1 = get_qty_after_transaction(item_code="_Test Item", warehouse="Stores - TCP1")

		self.assertEqual(actual_qty_0 - 5, actual_qty_1)

		# outgoing_rate
		outgoing_rate = (
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Sales Invoice", "voucher_no": si.name},
				"stock_value_difference",
			)
			/ 5
		)

		# return entry
		si1 = create_sales_invoice(
			is_return=1,
			return_against=si.name,
			qty=-2,
			rate=500,
			update_stock=1,
			company="_Test Company with perpetual inventory",
			debit_to="Debtors - TCP1",
			item_code="_Test Item",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		actual_qty_2 = get_qty_after_transaction(item_code="_Test Item", warehouse="Stores - TCP1")
		self.assertEqual(actual_qty_1 + 2, actual_qty_2)

		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si1.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(flt(incoming_rate, 3), abs(flt(outgoing_rate, 3)))
		stock_in_hand_account = get_inventory_account(
			"_Test Company with perpetual inventory", si1.items[0].warehouse
		)

		# Check gl entry
		gle_warehouse_amount = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si1.name, "account": stock_in_hand_account},
			"debit",
		)

		self.assertEqual(gle_warehouse_amount, stock_value_difference)

		party_credited = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Sales Invoice",
				"voucher_no": si1.name,
				"account": "Debtors - TCP1",
				"party": "_Test Customer",
			},
			"credit",
		)

		self.assertEqual(party_credited, 1000)

		# Check outstanding amount
		self.assertEqual(frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount"), -1000)
		self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"), 2500)

	def test_zero_qty_return_invoice_with_stock_effect(self):
		cr_note = create_sales_invoice(qty=-1, rate=300, is_return=1, do_not_submit=True)
		cr_note.update_stock = True
		cr_note.items[0].qty = 0
		self.assertRaises(frappe.ValidationError, cr_note.save)

	def test_return_invoice_with_account_mismatch(self):
		debtors2 = create_account(
			parent_account="Accounts Receivable - _TC",
			account_name="Debtors 2",
			company="_Test Company",
			account_type="Receivable",
		)
		si = create_sales_invoice(qty=1, rate=1000)
		cr_note = create_sales_invoice(
			qty=-1, rate=1000, is_return=1, return_against=si.name, debit_to=debtors2, do_not_save=True
		)
		self.assertRaises(frappe.ValidationError, cr_note.save)

	def test_gle_made_when_asset_is_returned(self):
		create_asset_data()
		asset = create_asset(item_code="Macbook Pro")

		si = create_sales_invoice(item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000)
		return_si = create_sales_invoice(
			is_return=1,
			return_against=si.name,
			item_code="Macbook Pro",
			asset=asset.name,
			qty=-1,
			rate=90000,
		)

		disposal_account = frappe.get_cached_value("Company", "_Test Company", "disposal_account")

		# Asset value is 100,000 but it was sold for 90,000, so there should be a loss of 10,000
		loss_for_si = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": si.name, "account": disposal_account},
			fields=["credit", "debit"],
		)[0]

		loss_for_return_si = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": return_si.name, "account": disposal_account},
			fields=["credit", "debit"],
		)[0]

		self.assertEqual(loss_for_si["credit"], loss_for_return_si["debit"])
		self.assertEqual(loss_for_si["debit"], loss_for_return_si["credit"])

	def test_incoming_rate_for_stand_alone_credit_note(self):
		return_si = create_sales_invoice(
			is_return=1,
			update_stock=1,
			qty=-1,
			rate=90000,
			incoming_rate=10,
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			debit_to="Debtors - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": return_si.name}, "incoming_rate"
		)
		debit_amount = frappe.db.get_value(
			"GL Entry", {"voucher_no": return_si.name, "account": "Stock In Hand - TCP1"}, "debit"
		)

		self.assertEqual(debit_amount, 10.0)
		self.assertEqual(incoming_rate, 10.0)

	def test_discount_on_net_total(self):
		si = frappe.copy_doc(test_records[2])
		si.apply_discount_on = "Net Total"
		si.discount_amount = 625
		si.insert()

		expected_values = {
			"keys": [
				"price_list_rate",
				"discount_percentage",
				"rate",
				"amount",
				"base_price_list_rate",
				"base_rate",
				"base_amount",
				"net_rate",
				"base_net_rate",
				"net_amount",
				"base_net_amount",
			],
			"_Test Item Home Desktop 100": [50, 0, 50, 500, 50, 50, 500, 25, 25, 250, 250],
			"_Test Item Home Desktop 200": [150, 0, 150, 750, 150, 150, 750, 75, 75, 375, 375],
		}

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values) - 1)

		# check if item values are calculated
		for d in si.get("items"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEqual(si.base_total, 1250)
		self.assertEqual(si.total, 1250)
		self.assertEqual(si.base_net_total, 625)
		self.assertEqual(si.net_total, 625)

		# check tax calculation
		expected_values = {
			"keys": [
				"tax_amount",
				"tax_amount_after_discount_amount",
				"base_tax_amount_after_discount_amount",
			],
			"_Test Account Shipping Charges - _TC": [100, 100, 100],
			"_Test Account Customs Duty - _TC": [62.5, 62.5, 62.5],
			"_Test Account Excise Duty - _TC": [70, 70, 70],
			"_Test Account Education Cess - _TC": [1.4, 1.4, 1.4],
			"_Test Account S&H Education Cess - _TC": [0.7, 0.7, 0.7],
			"_Test Account CST - _TC": [17.19, 17.19, 17.19],
			"_Test Account VAT - _TC": [78.12, 78.12, 78.12],
			"_Test Account Discount - _TC": [-95.49, -95.49, -95.49],
		}

		for d in si.get("taxes"):
			for i, k in enumerate(expected_values["keys"]):
				if expected_values.get(d.account_head):
					self.assertEqual(d.get(k), expected_values[d.account_head][i])

		self.assertEqual(si.total_taxes_and_charges, 234.42)
		self.assertEqual(si.base_grand_total, 859.42)
		self.assertEqual(si.grand_total, 859.42)

	def test_multi_currency_gle(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		gl_entries = frappe.db.sql(
			"""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = {
			"_Test Receivable USD - _TC": {
				"account_currency": "USD",
				"debit": 5000,
				"debit_in_account_currency": 100,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
			"Sales - _TC": {
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 5000,
				"credit_in_account_currency": 5000,
			},
		}

		for field in (
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		):
			for _i, gle in enumerate(gl_entries):
				self.assertEqual(expected_values[gle.account][field], gle[field])

		# cancel
		si.cancel()

		gle = frappe.db.sql(
			"""select name from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			si.name,
		)

		self.assertTrue(gle)

	def test_gle_in_transaction_currency(self):
		# create multi currency sales invoice with 2 items with same income account
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
			do_not_submit=True,
		)
		# add 2nd item with same income account
		si.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 80,
				"income_account": "Sales - _TC",
				"cost_center": "_Test Cost Center - _TC",
			},
		)
		si.submit()

		gl_entries = frappe.db.sql(
			"""select transaction_currency, transaction_exchange_rate,
			debit_in_transaction_currency, credit_in_transaction_currency
			from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s and account = 'Sales - _TC'
			order by account asc""",
			si.name,
			as_dict=1,
		)

		expected_gle = {
			"transaction_currency": "USD",
			"transaction_exchange_rate": 50,
			"debit_in_transaction_currency": 0,
			"credit_in_transaction_currency": 180,
		}

		for gle in gl_entries:
			for field in expected_gle:
				self.assertEqual(expected_gle[field], gle[field])

	def test_invoice_exchange_rate(self):
		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=1,
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, si.save)

	def test_invalid_currency(self):
		# Customer currency = USD

		# Transaction currency cannot be INR
		si1 = create_sales_invoice(
			customer="_Test Customer USD", debit_to="_Test Receivable USD - _TC", do_not_save=True
		)

		self.assertRaises(InvalidCurrency, si1.save)

		# Transaction currency cannot be EUR
		si2 = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="EUR",
			conversion_rate=80,
			do_not_save=True,
		)

		self.assertRaises(InvalidCurrency, si2.save)

		# Transaction currency only allowed in USD
		si3 = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		# Party Account currency must be in USD, as there is existing GLE with USD
		si4 = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="Debtors - _TC",
			currency="USD",
			conversion_rate=50,
			do_not_submit=True,
		)

		self.assertRaises(InvalidAccountCurrency, si4.submit)

		# Party Account currency must be in USD, force customer currency as there is no GLE

		si3.cancel()
		si5 = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="Debtors - _TC",
			currency="USD",
			conversion_rate=50,
			do_not_submit=True,
		)

		self.assertRaises(InvalidAccountCurrency, si5.submit)

	def test_create_so_with_margin(self):
		si = create_sales_invoice(item_code="_Test Item", qty=1, do_not_submit=True)
		price_list_rate = flt(100) * flt(si.plc_conversion_rate)
		si.items[0].price_list_rate = price_list_rate
		si.items[0].margin_type = "Percentage"
		si.items[0].margin_rate_or_amount = 25
		si.items[0].discount_amount = 0.0
		si.items[0].discount_percentage = 0.0
		si.save()
		self.assertEqual(si.get("items")[0].rate, flt((price_list_rate * 25) / 100 + price_list_rate))

	def test_outstanding_amount_after_advance_jv_cancellation(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import (
			test_records as jv_test_records,
		)

		jv = frappe.copy_doc(jv_test_records[0])
		jv.accounts[0].is_advance = "Yes"
		jv.insert()
		jv.submit()

		si = frappe.copy_doc(test_records[0])
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": "Journal Entry",
				"reference_name": jv.name,
				"reference_row": jv.get("accounts")[0].name,
				"advance_amount": 400,
				"allocated_amount": 300,
				"remarks": jv.remark,
			},
		)
		si.insert()
		si.submit()
		si.load_from_db()

		# check outstanding after advance allocation
		self.assertEqual(
			flt(si.outstanding_amount),
			flt(si.rounded_total - si.total_advance, si.precision("outstanding_amount")),
		)

		# added to avoid Document has been modified exception
		jv = frappe.get_doc("Journal Entry", jv.name)
		jv.cancel()

		si.load_from_db()
		# check outstanding after advance cancellation
		self.assertEqual(
			flt(si.outstanding_amount),
			flt(si.rounded_total + si.total_advance, si.precision("outstanding_amount")),
		)

	def test_outstanding_amount_after_advance_payment_entry_cancellation(self):
		"""Test impact of advance PE submission/cancellation on SI and SO."""
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		sales_order = make_sales_order(item_code="138-CMS Shoe", qty=1, price_list_rate=500)
		pe = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Receive",
				"party_type": "Customer",
				"party": "_Test Customer",
				"company": "_Test Company",
				"paid_from_account_currency": "INR",
				"paid_to_account_currency": "INR",
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"reference_no": "1",
				"reference_date": nowdate(),
				"received_amount": 300,
				"paid_amount": 300,
				"paid_from": "Debtors - _TC",
				"paid_to": "_Test Cash - _TC",
			}
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Sales Order",
				"reference_name": sales_order.name,
				"total_amount": sales_order.grand_total,
				"outstanding_amount": sales_order.grand_total,
				"allocated_amount": 300,
			},
		)
		pe.insert()
		pe.submit()

		sales_order.reload()
		self.assertEqual(sales_order.advance_paid, 300)

		si = frappe.copy_doc(test_records[0])
		si.items[0].sales_order = sales_order.name
		si.items[0].so_detail = sales_order.get("items")[0].name
		si.is_pos = 0
		si.append(
			"advances",
			{
				"doctype": "Sales Invoice Advance",
				"reference_type": "Payment Entry",
				"reference_name": pe.name,
				"reference_row": pe.references[0].name,
				"advance_amount": 300,
				"allocated_amount": 300,
				"remarks": pe.remarks,
			},
		)
		si.insert()
		si.submit()

		si.reload()
		pe.reload()
		sales_order.reload()

		# Check if SO is unlinked/replaced by SI in PE & if SO advance paid is 0
		self.assertEqual(pe.references[0].reference_name, si.name)
		self.assertEqual(sales_order.advance_paid, 0.0)

		# check outstanding after advance allocation
		self.assertEqual(
			flt(si.outstanding_amount),
			flt(si.rounded_total - si.total_advance, si.precision("outstanding_amount")),
		)

		pe.cancel()
		si.reload()

		# check outstanding after advance cancellation
		self.assertEqual(
			flt(si.outstanding_amount),
			flt(si.rounded_total + si.total_advance, si.precision("outstanding_amount")),
		)

	def test_multiple_uom_in_selling(self):
		frappe.db.sql(
			"""delete from `tabItem Price`
			where price_list='_Test Price List' and item_code='_Test Item'"""
		)
		item_price = frappe.new_doc("Item Price")
		item_price.price_list = "_Test Price List"
		item_price.item_code = "_Test Item"
		item_price.price_list_rate = 100
		item_price.insert()

		si = frappe.copy_doc(test_records[1])
		si.items[0].uom = "_Test UOM 1"
		si.items[0].conversion_factor = None
		si.items[0].price_list_rate = None
		si.save()

		expected_values = {
			"keys": [
				"price_list_rate",
				"stock_uom",
				"uom",
				"conversion_factor",
				"rate",
				"amount",
				"base_price_list_rate",
				"base_rate",
				"base_amount",
			],
			"_Test Item": [1000, "_Test UOM", "_Test UOM 1", 10.0, 1000, 1000, 1000, 1000, 1000],
		}

		# check if the conversion_factor and price_list_rate is calculated according to uom
		for d in si.get("items"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.item_code][i])

	def test_item_wise_tax_breakup(self):
		frappe.flags.country = "United States"

		si = self.create_si_to_test_tax_breakup()

		itemised_tax_data = get_itemised_tax_breakup_data(si)

		expected_itemised_tax = [
			{
				"item": "_Test Item",
				"taxable_amount": 10000.0,
				"Service Tax": {"tax_rate": 10.0, "tax_amount": 1000.0},
			},
			{
				"item": "_Test Item 2",
				"taxable_amount": 5000.0,
				"Service Tax": {"tax_rate": 10.0, "tax_amount": 500.0},
			},
		]

		self.assertEqual(itemised_tax_data, expected_itemised_tax)

		frappe.flags.country = None

	def create_si_to_test_tax_breakup(self):
		si = create_sales_invoice(qty=100, rate=50, do_not_save=True)
		si.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 100,
				"rate": 50,
				"income_account": "Sales - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
			},
		)
		si.append(
			"items",
			{
				"item_code": "_Test Item 2",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 100,
				"rate": 50,
				"income_account": "Sales - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
			},
		)

		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 10,
			},
		)
		si.insert()
		return si

	def test_company_monthly_sales(self):
		existing_current_month_sales = frappe.get_cached_value(
			"Company", "_Test Company", "total_monthly_sales"
		)

		si = create_sales_invoice()
		current_month_sales = frappe.get_cached_value("Company", "_Test Company", "total_monthly_sales")
		self.assertEqual(current_month_sales, existing_current_month_sales + si.base_grand_total)

		si.cancel()
		current_month_sales = frappe.get_cached_value("Company", "_Test Company", "total_monthly_sales")
		self.assertEqual(current_month_sales, existing_current_month_sales)

	def test_rounding_adjustment(self):
		si = create_sales_invoice(rate=24900, do_not_save=True)
		for tax in ["Tax 1", "Tax2"]:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": "_Test Account Service Tax - _TC",
					"description": tax,
					"rate": 14,
					"cost_center": "_Test Cost Center - _TC",
					"included_in_print_rate": 1,
				},
			)
		si.save()
		si.submit()
		self.assertEqual(si.net_total, 19453.12)
		self.assertEqual(si.grand_total, 24900)
		self.assertEqual(si.total_taxes_and_charges, 5446.88)
		self.assertEqual(si.rounding_adjustment, 0.0)

		expected_values = dict(
			(d[0], d)
			for d in [
				[si.debit_to, 24900, 0.0],
				["_Test Account Service Tax - _TC", 0.0, 5446.88],
				["Sales - _TC", 0.0, 19453.12],
				["Round Off - _TC", 0.01, 0.0],
			]
		)

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def test_rounding_adjustment_2(self):
		si = create_sales_invoice(rate=400, do_not_save=True)
		for rate in [400, 600, 100]:
			si.append(
				"items",
				{
					"item_code": "_Test Item",
					"warehouse": "_Test Warehouse - _TC",
					"qty": 1,
					"rate": rate,
					"income_account": "Sales - _TC",
					"cost_center": "_Test Cost Center - _TC",
				},
			)
		for tax_account in ["_Test Account VAT - _TC", "_Test Account Service Tax - _TC"]:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax_account,
					"description": tax_account,
					"rate": 9,
					"cost_center": "_Test Cost Center - _TC",
					"included_in_print_rate": 1,
				},
			)
		si.save()
		si.submit()
		self.assertEqual(si.net_total, 1271.19)
		self.assertEqual(si.grand_total, 1500)
		self.assertEqual(si.total_taxes_and_charges, 228.82)
		self.assertEqual(si.rounding_adjustment, -0.01)

		round_off_account = frappe.get_cached_value("Company", "_Test Company", "round_off_account")
		expected_values = {
			"_Test Account Service Tax - _TC": [0.0, 114.41],
			"_Test Account VAT - _TC": [0.0, 114.41],
			si.debit_to: [1500, 0.0],
			round_off_account: [0.01, 0.01],
			"Sales - _TC": [0.0, 1271.18],
		}

		gl_entries = frappe.db.sql(
			"""select account, sum(debit) as debit, sum(credit) as credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			group by account
			order by account asc""",
			si.name,
			as_dict=1,
		)

		for gle in gl_entries:
			expected_account_values = expected_values[gle.account]
			self.assertEqual(expected_account_values[0], gle.debit)
			self.assertEqual(expected_account_values[1], gle.credit)

	def test_rounding_adjustment_3(self):
		from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import (
			create_dimension,
			disable_dimension,
		)

		create_dimension()

		si = create_sales_invoice(do_not_save=True)
		si.items = []
		for d in [(1122, 2), (1122.01, 1), (1122.01, 1)]:
			si.append(
				"items",
				{
					"item_code": "_Test Item",
					"gst_hsn_code": "999800",
					"warehouse": "_Test Warehouse - _TC",
					"qty": d[1],
					"rate": d[0],
					"income_account": "Sales - _TC",
					"cost_center": "_Test Cost Center - _TC",
				},
			)
		for tax_account in ["_Test Account VAT - _TC", "_Test Account Service Tax - _TC"]:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax_account,
					"description": tax_account,
					"rate": 6,
					"cost_center": "_Test Cost Center - _TC",
					"included_in_print_rate": 1,
				},
			)

		si.cost_center = "_Test Cost Center 2 - _TC"
		si.location = "Block 1"

		si.save()
		si.submit()
		self.assertEqual(si.net_total, 4007.16)
		self.assertEqual(si.grand_total, 4488.02)
		self.assertEqual(si.total_taxes_and_charges, 480.86)
		self.assertEqual(si.rounding_adjustment, -0.02)

		round_off_account = frappe.get_cached_value("Company", "_Test Company", "round_off_account")
		expected_values = dict(
			(d[0], d)
			for d in [
				[si.debit_to, 4488.0, 0.0],
				["_Test Account Service Tax - _TC", 0.0, 240.43],
				["_Test Account VAT - _TC", 0.0, 240.43],
				["Sales - _TC", 0.0, 4007.15],
				[round_off_account, 0.02, 0.01],
			]
		)

		gl_entries = frappe.db.sql(
			"""select account, sum(debit) as debit, sum(credit) as credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			group by account
			order by account asc""",
			si.name,
			as_dict=1,
		)

		debit_credit_diff = 0
		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)
			debit_credit_diff += gle.debit - gle.credit

		self.assertEqual(debit_credit_diff, 0)

		round_off_gle = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Round Off - _TC"},
			["cost_center", "location"],
			as_dict=1,
		)

		if round_off_gle:
			self.assertEqual(round_off_gle.cost_center, "_Test Cost Center 2 - _TC")
			self.assertEqual(round_off_gle.location, "Block 1")

		disable_dimension()

	def test_sales_invoice_with_shipping_rule(self):
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule

		shipping_rule = create_shipping_rule(
			shipping_rule_type="Selling", shipping_rule_name="Shipping Rule - Sales Invoice Test"
		)

		si = frappe.copy_doc(test_records[2])

		si.shipping_rule = shipping_rule.name
		si.insert()
		si.save()

		self.assertEqual(si.net_total, 1250)

		self.assertEqual(si.total_taxes_and_charges, 468.85)
		self.assertEqual(si.grand_total, 1718.85)

	def test_create_invoice_without_terms(self):
		si = create_sales_invoice(do_not_save=1)
		self.assertFalse(si.get("payment_schedule"))

		si.insert()
		self.assertTrue(si.get("payment_schedule"))

	def test_duplicate_due_date_in_terms(self):
		si = create_sales_invoice(do_not_save=1)
		si.append("payment_schedule", dict(due_date="2017-01-01", invoice_portion=50.00, payment_amount=50))
		si.append("payment_schedule", dict(due_date="2017-01-01", invoice_portion=50.00, payment_amount=50))

		self.assertRaises(frappe.ValidationError, si.insert)

	def test_credit_note(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		si = create_sales_invoice(item_code="_Test Item", qty=(5 * -1), rate=500, is_return=1)

		outstanding_amount = get_outstanding_amount(
			si.doctype, si.name, "Debtors - _TC", si.customer, "Customer"
		)

		self.assertEqual(si.outstanding_amount, outstanding_amount)

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = si.currency
		pe.paid_to_account_currency = si.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = si.grand_total * -1
		pe.insert()
		pe.submit()

		si_doc = frappe.get_doc("Sales Invoice", si.name)
		self.assertEqual(si_doc.outstanding_amount, 0)

	def test_sales_invoice_with_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		si = create_sales_invoice_against_cost_center(cost_center=cost_center, debit_to="Debtors - _TC")
		self.assertEqual(si.cost_center, cost_center)

		expected_values = {
			"Debtors - _TC": {"cost_center": cost_center},
			"Sales - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_sales_invoice_with_project_link(self):
		from erpnext.projects.doctype.project.test_project import make_project

		project = make_project(
			{
				"project_name": "Sales Invoice Project",
				"project_template_name": "Test Project Template",
				"start_date": "2020-01-01",
			}
		)
		item_project = make_project(
			{
				"project_name": "Sales Invoice Item Project",
				"project_template_name": "Test Project Template",
				"start_date": "2019-06-01",
			}
		)

		sales_invoice = create_sales_invoice(do_not_save=1)
		sales_invoice.items[0].project = item_project.name
		sales_invoice.project = project.name

		sales_invoice.submit()

		expected_values = {
			"Debtors - _TC": {"project": project.name},
			"Sales - _TC": {"project": item_project.name},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, project, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			sales_invoice.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["project"], gle.project)

	def test_sales_invoice_without_cost_center(self):
		cost_center = "_Test Cost Center - _TC"
		si = create_sales_invoice(debit_to="Debtors - _TC")

		expected_values = {
			"Debtors - _TC": {"cost_center": None},
			"Sales - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""",
			si.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_deferred_revenue(self):
		deferred_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		item = create_item("_Test Item for Deferred Accounting")
		item.enable_deferred_revenue = 1
		item.item_defaults[0].deferred_revenue_account = deferred_account
		item.no_of_months = 12
		item.save()

		si = create_sales_invoice(item=item.name, posting_date="2019-01-10", do_not_submit=True)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2019-01-10"
		si.items[0].service_end_date = "2019-03-15"
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()

		pda1 = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2019-01-01",
				end_date="2019-03-31",
				type="Income",
				company="_Test Company",
			)
		)

		pda1.insert()
		pda1.submit()

		expected_gle = [
			[deferred_account, 33.85, 0.0, "2019-01-31"],
			["Sales - _TC", 0.0, 33.85, "2019-01-31"],
			[deferred_account, 43.08, 0.0, "2019-02-28"],
			["Sales - _TC", 0.0, 43.08, "2019-02-28"],
			[deferred_account, 23.07, 0.0, "2019-03-15"],
			["Sales - _TC", 0.0, 23.07, "2019-03-15"],
		]

		check_gl_entries(self, si.name, expected_gle, "2019-01-30")

	def test_deferred_revenue_missing_account(self):
		si = create_sales_invoice(posting_date="2019-01-10", do_not_submit=True)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2019-01-10"
		si.items[0].service_end_date = "2019-03-15"

		self.assertRaises(frappe.ValidationError, si.save)

	def test_fixed_deferred_revenue(self):
		deferred_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_based_on = "Months"
		acc_settings.save()

		item = create_item("_Test Item for Deferred Accounting")
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = deferred_account
		item.no_of_months = 12
		item.save()

		si = create_sales_invoice(item=item.name, posting_date="2019-01-16", rate=50000, do_not_submit=True)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2019-01-16"
		si.items[0].service_end_date = "2019-03-31"
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()

		pda1 = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date="2019-03-31",
				start_date="2019-01-01",
				end_date="2019-03-31",
				type="Income",
				company="_Test Company",
			)
		)

		pda1.insert()
		pda1.submit()

		expected_gle = [
			[deferred_account, 10000.0, 0.0, "2019-01-31"],
			["Sales - _TC", 0.0, 10000.0, "2019-01-31"],
			[deferred_account, 20000.0, 0.0, "2019-02-28"],
			["Sales - _TC", 0.0, 20000.0, "2019-02-28"],
			[deferred_account, 20000.0, 0.0, "2019-03-31"],
			["Sales - _TC", 0.0, 20000.0, "2019-03-31"],
		]

		check_gl_entries(self, si.name, expected_gle, "2019-01-30")

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_based_on = "Days"
		acc_settings.save()

	def test_inter_company_transaction(self):
		si = create_sales_invoice(
			company="Wind Power LLC",
			customer="_Test Internal Customer",
			debit_to="Debtors - WP",
			warehouse="Stores - WP",
			income_account="Sales - WP",
			expense_account="Cost of Goods Sold - WP",
			cost_center="Main - WP",
			currency="USD",
			do_not_save=1,
		)

		si.selling_price_list = "_Test Price List Rest of the World"
		si.submit()

		target_doc = make_inter_company_transaction("Sales Invoice", si.name)
		target_doc.items[0].update(
			{
				"expense_account": "Cost of Goods Sold - _TC1",
				"cost_center": "Main - _TC1",
				"warehouse": "Stores - _TC1",
			}
		)
		target_doc.submit()

		self.assertEqual(target_doc.company, "_Test Company 1")
		self.assertEqual(target_doc.supplier, "_Test Internal Supplier")

	def test_inter_company_transaction_without_default_warehouse(self):
		"Check mapping (expense account) of inter company SI to PI in absence of default warehouse."
		# setup
		old_negative_stock = frappe.db.get_single_value("Stock Settings", "allow_negative_stock")
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

		old_perpetual_inventory = erpnext.is_perpetual_inventory_enabled("_Test Company 1")
		frappe.local.enable_perpetual_inventory["_Test Company 1"] = 1

		frappe.db.set_value(
			"Company",
			"_Test Company 1",
			"stock_received_but_not_billed",
			"Stock Received But Not Billed - _TC1",
		)
		frappe.db.set_value(
			"Company",
			"_Test Company 1",
			"expenses_included_in_valuation",
			"Expenses Included In Valuation - _TC1",
		)

		# begin test
		si = create_sales_invoice(
			company="Wind Power LLC",
			customer="_Test Internal Customer",
			debit_to="Debtors - WP",
			warehouse="Stores - WP",
			income_account="Sales - WP",
			expense_account="Cost of Goods Sold - WP",
			cost_center="Main - WP",
			currency="USD",
			update_stock=1,
			do_not_save=1,
		)
		si.selling_price_list = "_Test Price List Rest of the World"
		si.submit()

		target_doc = make_inter_company_transaction("Sales Invoice", si.name)

		# in absence of warehouse Stock Received But Not Billed is set as expense account while mapping
		# mapping is not obstructed
		self.assertIsNone(target_doc.items[0].warehouse)
		self.assertEqual(target_doc.items[0].expense_account, "Stock Received But Not Billed - _TC1")

		target_doc.items[0].update({"cost_center": "Main - _TC1"})

		# missing warehouse is validated on save, after mapping
		self.assertRaises(WarehouseMissingError, target_doc.save)

		target_doc.items[0].update({"warehouse": "Stores - _TC1"})
		target_doc.save()

		# after warehouse is set, linked account or default inventory account is set
		self.assertEqual(target_doc.items[0].expense_account, "Stock In Hand - _TC1")

		# tear down
		frappe.local.enable_perpetual_inventory["_Test Company 1"] = old_perpetual_inventory
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", old_negative_stock)

	def test_sle_for_target_warehouse(self):
		se = make_stock_entry(
			item_code="138-CMS Shoe",
			target="Finished Goods - _TC",
			company="_Test Company",
			qty=1,
			basic_rate=500,
		)

		si = frappe.copy_doc(test_records[0])
		si.customer = "_Test Internal Customer 3"
		si.update_stock = 1
		si.set_warehouse = "Finished Goods - _TC"
		si.set_target_warehouse = "Stores - _TC"
		si.get("items")[0].warehouse = "Finished Goods - _TC"
		si.get("items")[0].target_warehouse = "Stores - _TC"
		si.insert()
		si.submit()

		sles = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": si.name}, fields=["name", "actual_qty"]
		)

		# check if both SLEs are created
		self.assertEqual(len(sles), 2)
		self.assertEqual(sum(d.actual_qty for d in sles), 0.0)

		# tear down
		si.cancel()
		se.cancel()

	def test_internal_transfer_gl_entry(self):
		si = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			customer="_Test Internal Customer 2",
			debit_to="Debtors - TCP1",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			currency="INR",
			do_not_save=1,
		)

		si.selling_price_list = "_Test Price List Rest of the World"
		si.update_stock = 1
		si.items[0].target_warehouse = "Work In Progress - TCP1"

		# Add stock to stores for successful stock transfer
		make_stock_entry(
			target="Stores - TCP1", company="_Test Company with perpetual inventory", qty=1, basic_rate=100
		)

		add_taxes(si)
		si.save()

		rate = 0.0
		for d in si.get("items"):
			rate = get_incoming_rate(
				{
					"item_code": d.item_code,
					"warehouse": d.warehouse,
					"posting_date": si.posting_date,
					"posting_time": si.posting_time,
					"qty": -1 * flt(d.get("stock_qty")),
					"serial_and_batch_bundle": d.serial_and_batch_bundle,
					"company": si.company,
					"voucher_type": "Sales Invoice",
					"voucher_no": si.name,
					"allow_zero_valuation": d.get("allow_zero_valuation"),
					"voucher_detail_no": d.name,
				},
				raise_error_if_no_rate=False,
			)

			rate = flt(rate, 2)

		si.submit()

		target_doc = make_inter_company_transaction("Sales Invoice", si.name)
		target_doc.company = "_Test Company with perpetual inventory"
		target_doc.items[0].warehouse = "Finished Goods - TCP1"
		add_taxes(target_doc)
		target_doc.save()
		target_doc.submit()

		tax_amount = flt(rate * (12 / 100), 2)
		si_gl_entries = [
			["_Test Account Excise Duty - TCP1", 0.0, tax_amount, nowdate()],
			["Unrealized Profit - TCP1", tax_amount, 0.0, nowdate()],
		]

		check_gl_entries(self, si.name, si_gl_entries, add_days(nowdate(), -1))

		pi_gl_entries = [
			["_Test Account Excise Duty - TCP1", tax_amount, 0.0, nowdate()],
			["Unrealized Profit - TCP1", 0.0, tax_amount, nowdate()],
		]

		# Sale and Purchase both should be at valuation rate
		self.assertEqual(si.items[0].rate, rate)
		self.assertEqual(target_doc.items[0].rate, rate)

		check_gl_entries(self, target_doc.name, pi_gl_entries, add_days(nowdate(), -1))

	def test_internal_transfer_gl_precision_issues(self):
		# Make a stock queue of an item with two valuations

		# Remove all existing stock for this
		if get_stock_balance("_Test Internal Transfer Item", "Stores - TCP1", "2022-04-10"):
			create_stock_reconciliation(
				item_code="_Test Internal Transfer Item",
				warehouse="Stores - TCP1",
				qty=0,
				rate=0,
				company="_Test Company with perpetual inventory",
				expense_account="Stock Adjustment - TCP1"
				if frappe.get_all("Stock Ledger Entry")
				else "Temporary Opening - TCP1",
				posting_date="2020-04-10",
				posting_time="14:00",
			)

		make_stock_entry(
			item_code="_Test Internal Transfer Item",
			target="Stores - TCP1",
			qty=9000000,
			basic_rate=52.0,
			posting_date="2020-04-10",
			posting_time="14:00",
		)
		make_stock_entry(
			item_code="_Test Internal Transfer Item",
			target="Stores - TCP1",
			qty=60000000,
			basic_rate=52.349777,
			posting_date="2020-04-10",
			posting_time="14:00",
		)

		# Make an internal transfer Sales Invoice Stock in non stock uom to check
		# for rounding errors while converting to stock uom
		si = create_sales_invoice(
			company="_Test Company with perpetual inventory",
			customer="_Test Internal Customer 2",
			item_code="_Test Internal Transfer Item",
			qty=5000000,
			uom="Box",
			debit_to="Debtors - TCP1",
			warehouse="Stores - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			currency="INR",
			do_not_save=1,
		)

		# Check GL Entries with precision
		si.update_stock = 1
		si.items[0].target_warehouse = "Work In Progress - TCP1"
		si.items[0].conversion_factor = 10
		si.save()
		si.submit()

		# Check if adjustment entry is created
		self.assertTrue(
			frappe.db.exists(
				"GL Entry",
				{
					"voucher_type": "Sales Invoice",
					"voucher_no": si.name,
					"remarks": "Rounding gain/loss Entry for Stock Transfer",
				},
			)
		)

	def test_item_tax_net_range(self):
		item = create_item("T Shirt")

		item.set("taxes", [])
		item.append(
			"taxes",
			{
				"item_tax_template": "_Test Account Excise Duty @ 10 - _TC",
				"minimum_net_rate": 0,
				"maximum_net_rate": 500,
			},
		)

		item.append(
			"taxes",
			{
				"item_tax_template": "_Test Account Excise Duty @ 12 - _TC",
				"minimum_net_rate": 501,
				"maximum_net_rate": 1000,
			},
		)

		item.save()

		sales_invoice = create_sales_invoice(item="T Shirt", rate=700, do_not_submit=True)
		self.assertEqual(sales_invoice.items[0].item_tax_template, "_Test Account Excise Duty @ 12 - _TC")

		# Apply discount
		sales_invoice.apply_discount_on = "Net Total"
		sales_invoice.discount_amount = 300
		sales_invoice.save()
		self.assertEqual(sales_invoice.items[0].item_tax_template, "_Test Account Excise Duty @ 10 - _TC")

	@change_settings("Selling Settings", {"enable_discount_accounting": 1})
	def test_sales_invoice_with_discount_accounting_enabled(self):
		discount_account = create_account(
			account_name="Discount Account",
			parent_account="Indirect Expenses - _TC",
			company="_Test Company",
		)
		si = create_sales_invoice(discount_account=discount_account, discount_percentage=10, rate=90)

		expected_gle = [
			["Debtors - _TC", 90.0, 0.0, nowdate()],
			["Discount Account - _TC", 10.0, 0.0, nowdate()],
			["Sales - _TC", 0.0, 100.0, nowdate()],
		]

		check_gl_entries(self, si.name, expected_gle, add_days(nowdate(), -1))

	@change_settings("Selling Settings", {"enable_discount_accounting": 1})
	def test_additional_discount_for_sales_invoice_with_discount_accounting_enabled(self):
		from erpnext.accounts.doctype.repost_accounting_ledger.test_repost_accounting_ledger import (
			update_repost_settings,
		)

		update_repost_settings()

		additional_discount_account = create_account(
			account_name="Discount Account",
			parent_account="Indirect Expenses - _TC",
			company="_Test Company",
		)

		create_account(
			account_name="TDS Payable",
			account_type="Tax",
			parent_account="Duties and Taxes - _TC",
			company="_Test Company",
		)

		si = create_sales_invoice(parent_cost_center="Main - _TC", do_not_save=1)
		si.apply_discount_on = "Grand Total"
		si.additional_discount_account = additional_discount_account
		si.additional_discount_percentage = 20
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "Main - _TC",
				"description": "Test",
				"rate": 10,
			},
		)
		si.submit()

		expected_gle = [
			["_Test Account VAT - _TC", 0.0, 10.0, nowdate()],
			["Debtors - _TC", 88, 0.0, nowdate()],
			["Discount Account - _TC", 22.0, 0.0, nowdate()],
			["Sales - _TC", 0.0, 100.0, nowdate()],
		]

		check_gl_entries(self, si.name, expected_gle, add_days(nowdate(), -1))

		# Update Invoice post submit and then check GL Entries again

		si.load_from_db()
		si.items[0].income_account = "Service - _TC"
		si.additional_discount_account = "_Test Account Sales - _TC"
		si.taxes[0].account_head = "TDS Payable - _TC"
		# Ledger reposted implicitly upon 'Update After Submit'
		si.save()

		expected_gle = [
			["_Test Account Sales - _TC", 22.0, 0.0, nowdate()],
			["Debtors - _TC", 88, 0.0, nowdate()],
			["Service - _TC", 0.0, 100.0, nowdate()],
			["TDS Payable - _TC", 0.0, 10.0, nowdate()],
		]

		check_gl_entries(self, si.name, expected_gle, add_days(nowdate(), -1))

	def test_asset_depreciation_on_sale_with_pro_rata(self):
		"""
		Tests if an Asset set to depreciate yearly on June 30, that gets sold on Sept 30, creates an additional depreciation entry on its date of sale.
		"""

		create_asset_data()
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, submit=1)
		post_depreciation_entries(getdate("2021-09-30"))

		create_sales_invoice(
			item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-09-30")
		)
		asset.load_from_db()

		expected_values = [
			["2020-06-30", 1366.12, 1366.12],
			["2021-06-30", 20000.0, 21366.12],
			["2021-09-30", 5041.1, 26407.22],
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
			self.assertTrue(schedule.journal_entry)

	def test_asset_depreciation_on_sale_without_pro_rata(self):
		"""
		Tests if an Asset set to depreciate yearly on Dec 31, that gets sold on Dec 31 after two years, created an additional depreciation entry on its date of sale.
		"""

		create_asset_data()
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date=getdate("2019-12-31"),
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date=getdate("2020-12-31"),
			submit=1,
		)

		post_depreciation_entries(getdate("2021-09-30"))

		create_sales_invoice(
			item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-12-31")
		)
		asset.load_from_db()

		expected_values = [["2020-12-31", 30000, 30000], ["2021-12-31", 30000, 60000]]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
			self.assertTrue(schedule.journal_entry)

	def test_depreciation_on_return_of_sold_asset(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		create_asset_data()
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, submit=1)
		post_depreciation_entries(getdate("2021-09-30"))

		si = create_sales_invoice(
			item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-09-30")
		)
		return_si = make_return_doc("Sales Invoice", si.name)
		return_si.submit()
		asset.load_from_db()

		expected_values = [
			["2020-06-30", 1366.12, 1366.12, True],
			["2021-06-30", 20000.0, 21366.12, True],
			["2022-06-30", 20000.0, 41366.12, False],
			["2023-06-30", 20000.0, 61366.12, False],
			["2024-06-30", 20000.0, 81366.12, False],
			["2025-06-06", 18633.88, 100000.0, False],
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
			self.assertEqual(schedule.journal_entry, schedule.journal_entry)

	def test_sales_invoice_against_supplier(self):
		from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
			make_customer,
		)
		from erpnext.accounts.doctype.party_link.party_link import create_party_link
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		# create a customer
		customer = make_customer(customer="_Test Common Supplier")
		# create a supplier
		supplier = create_supplier(supplier_name="_Test Common Supplier").name

		# create a party link between customer & supplier
		party_link = create_party_link("Supplier", supplier, customer)

		# enable common party accounting
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 1)

		# create a sales invoice
		si = create_sales_invoice(customer=customer, parent_cost_center="_Test Cost Center - _TC")

		# check outstanding of sales invoice
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(flt(si.outstanding_amount), 0.0)

		# check creation of journal entry
		jv = frappe.get_all(
			"Journal Entry Account",
			{
				"account": si.debit_to,
				"party_type": "Customer",
				"party": si.customer,
				"reference_type": si.doctype,
				"reference_name": si.name,
			},
			pluck="credit_in_account_currency",
		)

		self.assertTrue(jv)
		self.assertEqual(jv[0], si.grand_total)

		party_link.delete()
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 0)

	def test_sales_invoice_against_supplier_usd_with_dimensions(self):
		from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
			make_customer,
		)
		from erpnext.accounts.doctype.party_link.party_link import create_party_link
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		# create a customer
		customer = make_customer(customer="_Test Common Supplier USD")
		cust_doc = frappe.get_doc("Customer", customer)
		cust_doc.default_currency = "USD"
		cust_doc.save()
		# create a supplier
		supplier = create_supplier(supplier_name="_Test Common Supplier USD").name
		supp_doc = frappe.get_doc("Supplier", supplier)
		supp_doc.default_currency = "USD"
		supp_doc.save()

		# create a party link between customer & supplier
		party_link = create_party_link("Supplier", supplier, customer)

		# enable common party accounting
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 1)

		# create a dimension and make it mandatory
		if not frappe.get_all("Accounting Dimension", filters={"document_type": "Department"}):
			dim = frappe.get_doc(
				{
					"doctype": "Accounting Dimension",
					"document_type": "Department",
					"dimension_defaults": [{"company": "_Test Company", "mandatory_for_bs": True}],
				}
			)
			dim.save()
		else:
			dim = frappe.get_doc(
				"Accounting Dimension",
				frappe.get_all("Accounting Dimension", filters={"document_type": "Department"})[0],
			)
			dim.disabled = False
			dim.dimension_defaults = []
			dim.append("dimension_defaults", {"company": "_Test Company", "mandatory_for_bs": True})
			dim.save()

		# create a sales invoice
		si = create_sales_invoice(
			customer=customer, parent_cost_center="_Test Cost Center - _TC", do_not_submit=True
		)
		si.department = "All Departments"
		si.save().submit()

		# check outstanding of sales invoice
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(flt(si.outstanding_amount), 0.0)

		# check creation of journal entry
		jv = frappe.get_all(
			"Journal Entry Account",
			{
				"account": si.debit_to,
				"party_type": "Customer",
				"party": si.customer,
				"reference_type": si.doctype,
				"reference_name": si.name,
				"department": "All Departments",
			},
			pluck="credit_in_account_currency",
		)

		self.assertTrue(jv)
		self.assertEqual(jv[0], si.grand_total)

		dim.disabled = True
		dim.save()
		party_link.delete()
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 0)

	def test_sales_invoice_cancel_with_common_party_advance_jv(self):
		from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
			make_customer,
		)
		from erpnext.accounts.doctype.party_link.party_link import create_party_link
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		# create a customer
		customer = make_customer(customer="_Test Common Supplier")
		# create a supplier
		supplier = create_supplier(supplier_name="_Test Common Supplier").name

		# create a party link between customer & supplier
		party_link = create_party_link("Supplier", supplier, customer)

		# enable common party accounting
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 1)

		# create a sales invoice
		si = create_sales_invoice(customer=customer)

		# check creation of journal entry
		jv = frappe.db.get_value(
			"Journal Entry Account",
			filters={
				"reference_type": si.doctype,
				"reference_name": si.name,
				"docstatus": 1,
			},
			fieldname="parent",
		)

		self.assertTrue(jv)

		# cancel sales invoice
		si.cancel()

		# check cancellation of journal entry
		jv_status = frappe.db.get_value("Journal Entry", jv, "docstatus")
		self.assertEqual(jv_status, 2)

		party_link.delete()
		frappe.db.set_single_value("Accounts Settings", "enable_common_party_accounting", 0)

	def test_payment_statuses(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		today = nowdate()

		# Test Overdue
		si = create_sales_invoice(do_not_submit=True)
		si.payment_schedule = []
		si.append(
			"payment_schedule",
			{"due_date": add_days(today, -5), "invoice_portion": 50, "payment_amount": si.grand_total / 2},
		)
		si.append(
			"payment_schedule",
			{"due_date": add_days(today, 5), "invoice_portion": 50, "payment_amount": si.grand_total / 2},
		)
		si.submit()
		self.assertEqual(si.status, "Overdue")

		# Test payment less than due amount
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_amount = 1
		pe.references[0].allocated_amount = pe.paid_amount
		pe.submit()
		si.reload()
		self.assertEqual(si.status, "Overdue")

		# Test Partly Paid
		pe = frappe.copy_doc(pe)
		pe.paid_amount = si.grand_total / 2
		pe.references[0].allocated_amount = pe.paid_amount
		pe.submit()
		si.reload()
		self.assertEqual(si.status, "Partly Paid")

		# Test Paid
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_amount = si.outstanding_amount
		pe.submit()
		si.reload()
		self.assertEqual(si.status, "Paid")

	def test_update_invoice_status(self):
		today = nowdate()

		# Sales Invoice without Payment Schedule
		si = create_sales_invoice(posting_date=add_days(today, -5))

		# Sales Invoice with Payment Schedule
		si_with_payment_schedule = create_sales_invoice(do_not_submit=True)
		si_with_payment_schedule.set(
			"payment_schedule",
			[
				{
					"due_date": add_days(today, -5),
					"invoice_portion": 50,
					"payment_amount": si_with_payment_schedule.grand_total / 2,
				},
				{
					"due_date": add_days(today, 5),
					"invoice_portion": 50,
					"payment_amount": si_with_payment_schedule.grand_total / 2,
				},
			],
		)
		si_with_payment_schedule.submit()

		for invoice in (si, si_with_payment_schedule):
			invoice.db_set("status", "Unpaid")
			update_invoice_status()
			invoice.reload()
			self.assertEqual(invoice.status, "Overdue")

			invoice.db_set("status", "Unpaid and Discounted")
			update_invoice_status()
			invoice.reload()
			self.assertEqual(invoice.status, "Overdue and Discounted")

	def test_sales_commission(self):
		si = frappe.copy_doc(test_records[2])

		frappe.db.set_value("Item", si.get("items")[0].item_code, "grant_commission", 1)
		frappe.db.set_value("Item", si.get("items")[1].item_code, "grant_commission", 0)

		item = copy.deepcopy(si.get("items")[0])
		item.update(
			{
				"qty": 1,
				"rate": 500,
			}
		)

		item = copy.deepcopy(si.get("items")[1])
		item.update(
			{
				"qty": 1,
				"rate": 500,
			}
		)

		# Test valid values
		for commission_rate, total_commission in ((0, 0), (10, 50), (100, 500)):
			si.commission_rate = commission_rate
			si.save()
			self.assertEqual(si.amount_eligible_for_commission, 500)
			self.assertEqual(si.total_commission, total_commission)

		# Test invalid values
		for commission_rate in (101, -1):
			si.reload()
			si.commission_rate = commission_rate
			self.assertRaises(frappe.ValidationError, si.save)

	@change_settings("Accounts Settings", {"acc_frozen_upto": add_days(getdate(), 1)})
	def test_sales_invoice_submission_post_account_freezing_date(self):
		si = create_sales_invoice(do_not_save=True)
		si.posting_date = add_days(getdate(), 1)
		si.save()

		self.assertRaises(frappe.ValidationError, si.submit)
		si.posting_date = getdate()
		si.submit()

	def test_over_billing_case_against_delivery_note(self):
		"""
		Test a case where duplicating the item with qty = 1 in the invoice
		allows overbilling even if it is disabled
		"""
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		over_billing_allowance = frappe.db.get_single_value("Accounts Settings", "over_billing_allowance")
		frappe.db.set_single_value("Accounts Settings", "over_billing_allowance", 0)

		dn = create_delivery_note()
		dn.submit()

		si = make_sales_invoice(dn.name)
		# make a copy of first item and add it to invoice
		item_copy = frappe.copy_doc(si.items[0])
		si.append("items", item_copy)
		si.save()

		with self.assertRaises(frappe.ValidationError) as err:
			si.submit()

		self.assertTrue("cannot overbill" in str(err.exception).lower())

		frappe.db.set_single_value("Accounts Settings", "over_billing_allowance", over_billing_allowance)

	@change_settings(
		"Accounts Settings",
		{
			"book_deferred_entries_via_journal_entry": 1,
			"submit_journal_entries": 1,
		},
	)
	def test_multi_currency_deferred_revenue_via_journal_entry(self):
		deferred_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)

		item = create_item("_Test Item for Deferred Accounting")
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_revenue_account = deferred_account
		item.save()

		si = create_sales_invoice(
			customer="_Test Customer USD",
			currency="USD",
			item=item.name,
			qty=1,
			rate=100,
			conversion_rate=60,
			do_not_save=True,
		)

		si.set_posting_time = 1
		si.posting_date = "2019-01-01"
		si.debit_to = "_Test Receivable USD - _TC"
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2019-01-01"
		si.items[0].service_end_date = "2019-03-30"
		si.items[0].deferred_expense_account = deferred_account
		si.save()
		si.submit()

		frappe.db.set_single_value("Accounts Settings", "acc_frozen_upto", getdate("2019-01-31"))

		pda1 = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2019-01-01",
				end_date="2019-03-31",
				type="Income",
				company="_Test Company",
			)
		)

		pda1.insert()
		pda1.submit()

		expected_gle = [
			["Sales - _TC", 0.0, 2089.89, "2019-01-28"],
			[deferred_account, 2089.89, 0.0, "2019-01-28"],
			["Sales - _TC", 0.0, 1887.64, "2019-02-28"],
			[deferred_account, 1887.64, 0.0, "2019-02-28"],
			["Sales - _TC", 0.0, 2022.47, "2019-03-15"],
			[deferred_account, 2022.47, 0.0, "2019-03-15"],
		]

		gl_entries = frappe.db.sql(
			"""select account, debit, credit, posting_date
			from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_detail_no=%s and posting_date <= %s
			order by posting_date asc, account asc""",
			(si.items[0].name, si.posting_date),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.credit)
			self.assertEqual(expected_gle[i][2], gle.debit)
			self.assertEqual(getdate(expected_gle[i][3]), gle.posting_date)

	def test_standalone_serial_no_return(self):
		si = create_sales_invoice(
			item_code="_Test Serialized Item With Series", update_stock=True, is_return=True, qty=-1
		)
		si.reload()
		self.assertTrue(get_serial_nos_from_bundle(si.items[0].serial_and_batch_bundle))

	def test_sales_invoice_with_disabled_account(self):
		try:
			account_name = "Sales Expenses - _TC"
			account = frappe.get_doc("Account", account_name)
			account.disabled = 1
			account.save()

			si = create_sales_invoice(do_not_save=True)
			si.posting_date = add_days(getdate(), 1)
			si.taxes = []

			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": account_name,
					"cost_center": "Main - _TC",
					"description": "Commission",
					"rate": 5,
				},
			)
			si.save()

			with self.assertRaises(frappe.ValidationError) as err:
				si.submit()

			self.assertTrue(
				"Cannot create accounting entries against disabled accounts" in str(err.exception)
			)

		finally:
			account.disabled = 0
			account.save()

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_gain_loss_with_advance_entry(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		jv = make_journal_entry("_Test Receivable USD - _TC", "_Test Bank - _TC", -7000, save=False)

		jv.accounts[0].exchange_rate = 70
		jv.accounts[0].credit_in_account_currency = 100
		jv.accounts[0].party_type = "Customer"
		jv.accounts[0].party = "_Test Customer USD"

		jv.save()
		jv.submit()

		si = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=75,
			do_not_save=1,
			rate=100,
		)

		si.append(
			"advances",
			{
				"reference_type": "Journal Entry",
				"reference_name": jv.name,
				"reference_row": jv.accounts[0].name,
				"advance_amount": 100,
				"allocated_amount": 100,
				"ref_exchange_rate": 70,
			},
		)
		si.save()
		si.submit()
		expected_gle = [
			["_Test Receivable USD - _TC", 7500.0, 0.0, nowdate()],
			["Sales - _TC", 0.0, 7500.0, nowdate()],
		]
		check_gl_entries(self, si.name, expected_gle, nowdate())

		si.reload()
		self.assertEqual(si.outstanding_amount, 0)
		journals = frappe.db.get_all(
			"Journal Entry Account",
			filters={"reference_type": "Sales Invoice", "reference_name": si.name, "docstatus": 1},
			pluck="parent",
		)
		journals = [x for x in journals if x != jv.name]
		self.assertEqual(len(journals), 1)
		je_type = frappe.get_cached_value("Journal Entry", journals[0], "voucher_type")
		self.assertEqual(je_type, "Exchange Gain Or Loss")
		frappe.db.get_all(
			"Payment Ledger Entry",
			filters={"against_voucher_no": si.name, "delinked": 0},
			fields=["sum(amount), sum(amount_in_account_currency)"],
			as_list=1,
		)

	def test_batch_expiry_for_sales_invoice_return(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			"_Test Batch Item For Return Check",
			{
				"is_purchase_item": 1,
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBIRC.#####",
			},
		)

		pr = make_purchase_receipt(qty=1, item_code=item.name)

		batch_no = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)
		si = create_sales_invoice(qty=1, item_code=item.name, update_stock=1, batch_no=batch_no)

		si.load_from_db()
		batch_no = get_batch_from_bundle(si.items[0].serial_and_batch_bundle)
		self.assertTrue(batch_no)

		frappe.db.set_value("Batch", batch_no, "expiry_date", add_days(today(), -1))

		return_si = make_return_doc(si.doctype, si.name)
		return_si.save().submit()

		self.assertTrue(return_si.docstatus == 1)

	def test_sales_invoice_with_payable_tax_account(self):
		si = create_sales_invoice(do_not_submit=True)
		si.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "Creditors - _TC",
				"description": "Test",
				"cost_center": "Main - _TC",
				"tax_amount": 10,
				"total": 10,
				"dont_recompute_tax": 0,
			},
		)
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_advance_entries_as_liability(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		advance_account = create_account(
			parent_account="Current Liabilities - _TC",
			account_name="Advances Received",
			company="_Test Company",
			account_type="Receivable",
		)

		set_advance_flag(company="_Test Company", flag=1, default_account=advance_account)

		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from=advance_account,
			paid_to="Cash - _TC",
			paid_amount=1000,
		)
		pe.submit()

		si = create_sales_invoice(
			company="_Test Company",
			customer="_Test Customer",
			do_not_save=True,
			do_not_submit=True,
			rate=500,
			price_list_rate=500,
		)
		si.base_grand_total = 500
		si.grand_total = 500
		si.set_advances()
		for advance in si.advances:
			advance.allocated_amount = 500 if advance.reference_name == pe.name else 0
		si.save()
		si.submit()

		self.assertEqual(si.advances[0].allocated_amount, 500)

		# Check GL Entry against payment doctype
		expected_gle = [
			["Advances Received - _TC", 0.0, 1000.0, nowdate()],
			["Advances Received - _TC", 500, 0.0, nowdate()],
			["Cash - _TC", 1000, 0.0, nowdate()],
			["Debtors - _TC", 0.0, 500, nowdate()],
		]

		check_gl_entries(self, pe.name, expected_gle, nowdate(), voucher_type="Payment Entry")

		si.load_from_db()
		self.assertEqual(si.outstanding_amount, 0)

		set_advance_flag(company="_Test Company", flag=0, default_account="")

	@change_settings("Selling Settings", {"customer_group": None, "territory": None})
	def test_sales_invoice_without_customer_group_and_territory(self):
		# create a customer
		if not frappe.db.exists("Customer", "_Test Simple Customer"):
			customer_dict = get_customer_dict("_Test Simple Customer")
			customer_dict.pop("customer_group")
			customer_dict.pop("territory")
			customer = frappe.get_doc(customer_dict).insert(ignore_permissions=True)

			self.assertEqual(customer.customer_group, None)
			self.assertEqual(customer.territory, None)

		# create a sales invoice
		si = create_sales_invoice(customer="_Test Simple Customer")
		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.customer_group, None)
		self.assertEqual(si.territory, None)

	@change_settings("Selling Settings", {"allow_negative_rates_for_items": 0})
	def test_sales_return_negative_rate(self):
		si = create_sales_invoice(is_return=1, qty=-2, rate=-10, do_not_save=True)
		self.assertRaises(frappe.ValidationError, si.save)

		si.items[0].rate = 10
		si.save()

	def test_partial_allocation_on_advance_as_liability(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		company = "_Test Company"
		customer = "_Test Customer"
		debtors_acc = "Debtors - _TC"
		advance_account = create_account(
			parent_account="Current Liabilities - _TC",
			account_name="Advances Received",
			company="_Test Company",
			account_type="Receivable",
		)

		set_advance_flag(company="_Test Company", flag=1, default_account=advance_account)

		pe = create_payment_entry(
			company=company,
			payment_type="Receive",
			party_type="Customer",
			party=customer,
			paid_from=advance_account,
			paid_to="Cash - _TC",
			paid_amount=1000,
		)
		pe.submit()

		si = create_sales_invoice(
			company=company,
			customer=customer,
			do_not_save=True,
			do_not_submit=True,
			rate=1000,
			price_list_rate=1000,
		)
		si.base_grand_total = 1000
		si.grand_total = 1000
		si.set_advances()
		for advance in si.advances:
			advance.allocated_amount = 200 if advance.reference_name == pe.name else 0
		si.save()
		si.submit()

		self.assertEqual(si.advances[0].allocated_amount, 200)

		# Check GL Entry against partial from advance
		expected_gle = [
			[advance_account, 0.0, 1000.0, nowdate()],
			[advance_account, 200.0, 0.0, nowdate()],
			["Cash - _TC", 1000.0, 0.0, nowdate()],
			[debtors_acc, 0.0, 200.0, nowdate()],
		]
		check_gl_entries(self, pe.name, expected_gle, nowdate(), voucher_type="Payment Entry")
		si.reload()
		self.assertEqual(si.outstanding_amount, 800.0)

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = company
		pr.party_type = "Customer"
		pr.party = customer
		pr.receivable_payable_account = debtors_acc
		pr.default_advance_account = advance_account
		pr.get_unreconciled_entries()

		# allocate some more of the same advance
		# self.assertEqual(len(pr.invoices), 1)
		# self.assertEqual(len(pr.payments), 1)
		invoices = [x.as_dict() for x in pr.invoices if x.get("invoice_number") == si.name]
		payments = [x.as_dict() for x in pr.payments if x.get("reference_name") == pe.name]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.allocation[0].allocated_amount = 300
		pr.reconcile()

		si.reload()
		self.assertEqual(si.outstanding_amount, 500.0)

		# Check GL Entry against multi partial allocations from advance
		expected_gle = [
			[advance_account, 0.0, 1000.0, nowdate()],
			[advance_account, 200.0, 0.0, nowdate()],
			[advance_account, 300.0, 0.0, nowdate()],
			["Cash - _TC", 1000.0, 0.0, nowdate()],
			[debtors_acc, 0.0, 200.0, nowdate()],
			[debtors_acc, 0.0, 300.0, nowdate()],
		]
		check_gl_entries(self, pe.name, expected_gle, nowdate(), voucher_type="Payment Entry")
		set_advance_flag(company="_Test Company", flag=0, default_account="")

	def test_loyalty_points_redemption_with_shopping_cart(self):
		from erpnext.accounts.doctype.loyalty_program.test_loyalty_program import (
			create_records,
			create_sales_invoice_record,
		)
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		# Set up loyalty program
		create_records()
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		create_sales_invoice_record(10).insert().submit()

		# Create a sales order
		so = make_sales_order(qty=10, do_not_save=True, customer="Test Loyalty Customer")
		so.name = "_T-Sales Order LP-0001"
		so.order_type = "Shopping Cart"
		so.loyalty_points = 50
		so.loyalty_amount = 50
		so.insert()
		so.submit()

		# Create sales invoice from the sales order
		si = make_sales_invoice(so.name)
		from frappe.model.trace import traced_field_context

		with traced_field_context(si.__class__, "loyalty_program", forbidden_values=[None]):
			si.insert()
		si.submit()

		# Check if loyalty points are applied correctly
		self.assertEqual(si.loyalty_program, "Test Single Loyalty")
		self.assertEqual(si.loyalty_points, 50)
		self.assertEqual(si.loyalty_amount, 50)

		# Check GL entries for loyalty points redemption
		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": si.name},
			fields=["account", "debit", "credit"],
		)

		loyalty_account = frappe.db.get_value("Loyalty Program", "Test Single Loyalty", "expense_account")
		expected_gl_entries = [
			{"account": si.debit_to, "debit": si.grand_total, "credit": 0},
			{"account": si.items[0].income_account, "debit": 0, "credit": si.net_total},
			{"account": loyalty_account, "debit": 50, "credit": 0},
		]

		for entry in expected_gl_entries:
			self.assertTrue(
				any(
					gl_entry.account == entry["account"]
					and gl_entry.debit == entry["debit"]
					and gl_entry.credit == entry["credit"]
					for gl_entry in gl_entries
				)
			)

	def test_pulling_advance_based_on_debit_to(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		debtors2 = create_account(
			parent_account="Accounts Receivable - _TC",
			account_name="Debtors 2",
			company="_Test Company",
			account_type="Receivable",
		)
		si = create_sales_invoice(do_not_submit=True)
		si.debit_to = debtors2
		si.save()

		pe = create_payment_entry(
			company=si.company,
			payment_type="Receive",
			party_type="Customer",
			party=si.customer,
			paid_from=debtors2,
			paid_to="Cash - _TC",
			paid_amount=1000,
		)
		pe.submit()
		advances = si.get_advance_entries()
		self.assertEqual(1, len(advances))
		self.assertEqual(advances[0].reference_name, pe.name)

	def test_taxes_merging_from_delivery_note(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn1 = create_delivery_note(do_not_submit=1)
		dn1.items[0].qty = 10
		dn1.items[0].rate = 100
		dn1.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "Freight and Forwarding Charges - _TC",
				"description": "movement charges",
				"tax_amount": 100,
			},
		)
		dn1.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "Marketing Expenses - _TC",
				"description": "marketing",
				"tax_amount": 150,
			},
		)
		dn1.save().submit()

		dn2 = create_delivery_note(do_not_submit=1)
		dn2.items[0].qty = 5
		dn2.items[0].rate = 100
		dn2.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "Freight and Forwarding Charges - _TC",
				"description": "movement charges",
				"tax_amount": 20,
			},
		)
		dn2.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "Miscellaneous Expenses - _TC",
				"description": "marketing",
				"tax_amount": 60,
			},
		)
		dn2.save().submit()

		# si = make_sales_invoice(dn1.name)
		si = create_sales_invoice(do_not_submit=True)
		si.customer = dn1.customer
		si.items.clear()

		from frappe.model.mapper import map_docs

		map_docs(
			method="erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
			source_names=json.dumps([dn1.name, dn2.name]),
			target_doc=si,
			args=json.dumps({"customer": dn1.customer, "merge_taxes": 1, "filtered_children": []}),
		)
		si.save().submit()

		expected = [
			{
				"charge_type": "Actual",
				"account_head": "Freight and Forwarding Charges - _TC",
				"tax_amount": 120.0,
				"total": 1520.0,
				"base_total": 1520.0,
			},
			{
				"charge_type": "Actual",
				"account_head": "Marketing Expenses - _TC",
				"tax_amount": 150.0,
				"total": 1670.0,
				"base_total": 1670.0,
			},
			{
				"charge_type": "Actual",
				"account_head": "Miscellaneous Expenses - _TC",
				"tax_amount": 60.0,
				"total": 1610.0,
				"base_total": 1610.0,
			},
		]
		actual = [
			dict(
				charge_type=x.charge_type,
				account_head=x.account_head,
				tax_amount=x.tax_amount,
				total=x.total,
				base_total=x.base_total,
			)
			for x in si.taxes
		]
		self.assertEqual(expected, actual)

	def test_pos_returns_without_update_outstanding_for_self(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		pos_profile = make_pos_profile()
		pos_profile.payments = []
		pos_profile.append("payments", {"default": 1, "mode_of_payment": "Cash"})
		pos_profile.save()

		pos = create_sales_invoice(qty=10, do_not_save=True)
		pos.is_pos = 1
		pos.pos_profile = pos_profile.name
		pos.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - _TC", "amount": 500}
		)
		pos.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 500})
		pos.save().submit()

		pos_return = make_sales_return(pos.name)
		pos_return.update_outstanding_for_self = False
		pos_return.save().submit()

		gle = qb.DocType("GL Entry")
		res = (
			qb.from_(gle)
			.select(gle.against_voucher)
			.distinct()
			.where(
				gle.is_cancelled.eq(0) & gle.voucher_no.eq(pos_return.name) & gle.against_voucher.notnull()
			)
			.run(as_list=1)
		)
		self.assertEqual(len(res), 1)
		self.assertEqual(res[0][0], pos_return.return_against)

	@change_settings("Accounts Settings", {"enable_common_party_accounting": True})
	def test_common_party_with_foreign_currency_jv(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import (
			make_customer,
		)
		from erpnext.accounts.doctype.party_link.party_link import create_party_link
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier
		from erpnext.setup.utils import get_exchange_rate

		creditors = create_account(
			account_name="Creditors USD",
			parent_account="Accounts Payable - _TC",
			company="_Test Company",
			account_currency="USD",
			account_type="Payable",
		)
		debtors = create_account(
			account_name="Debtors USD",
			parent_account="Accounts Receivable - _TC",
			company="_Test Company",
			account_currency="USD",
			account_type="Receivable",
		)

		# create a customer
		customer = make_customer(customer="_Test Common Party USD")
		cust_doc = frappe.get_doc("Customer", customer)
		cust_doc.default_currency = "USD"
		test_account_details = {
			"company": "_Test Company",
			"account": debtors,
		}
		cust_doc.append("accounts", test_account_details)
		cust_doc.save()

		# create a supplier
		supplier = create_supplier(supplier_name="_Test Common Party USD").name
		supp_doc = frappe.get_doc("Supplier", supplier)
		supp_doc.default_currency = "USD"
		test_account_details = {
			"company": "_Test Company",
			"account": creditors,
		}
		supp_doc.append("accounts", test_account_details)
		supp_doc.save()

		# create a party link between customer & supplier
		create_party_link("Supplier", supplier, customer)

		# create a sales invoice
		si = create_sales_invoice(
			customer=customer,
			currency="USD",
			conversion_rate=get_exchange_rate("USD", "INR"),
			debit_to=debtors,
			do_not_save=1,
		)
		si.party_account_currency = "USD"
		si.save()
		si.submit()

		# check outstanding of sales invoice
		si.reload()
		self.assertEqual(si.status, "Paid")
		self.assertEqual(flt(si.outstanding_amount), 0.0)

		# check creation of journal entry
		jv = frappe.get_all(
			"Journal Entry Account",
			{
				"account": si.debit_to,
				"party_type": "Customer",
				"party": si.customer,
				"reference_type": si.doctype,
				"reference_name": si.name,
			},
			pluck="credit_in_account_currency",
		)
		self.assertTrue(jv)
		self.assertEqual(jv[0], si.grand_total)

	def test_invoice_remarks(self):
		si = frappe.copy_doc(test_records[0])
		si.po_no = "Test PO"
		si.po_date = nowdate()
		si.save()
		si.submit()
		self.assertEqual(si.remarks, f"Against Customer Order Test PO dated {format_date(nowdate())}")


def set_advance_flag(company, flag, default_account):
	frappe.db.set_value(
		"Company",
		company,
		{
			"book_advance_payments_in_separate_party_account": flag,
			"default_advance_received_account": default_account,
		},
	)


def check_gl_entries(doc, voucher_no, expected_gle, posting_date, voucher_type="Sales Invoice"):
	gl = frappe.qb.DocType("GL Entry")
	q = (
		frappe.qb.from_(gl)
		.select(gl.account, gl.debit, gl.credit, gl.posting_date)
		.where(
			(gl.voucher_type == voucher_type)
			& (gl.voucher_no == voucher_no)
			& (gl.posting_date >= posting_date)
			& (gl.is_cancelled == 0)
		)
		.orderby(gl.posting_date, gl.account, gl.creation)
	)
	gl_entries = q.run(as_dict=True)

	for i, gle in enumerate(gl_entries):
		doc.assertEqual(expected_gle[i][0], gle.account)
		doc.assertEqual(expected_gle[i][1], gle.debit)
		doc.assertEqual(expected_gle[i][2], gle.credit)
		doc.assertEqual(getdate(expected_gle[i][3]), gle.posting_date)


def create_sales_invoice(**args):
	si = frappe.new_doc("Sales Invoice")
	args = frappe._dict(args)
	if args.posting_date:
		si.set_posting_time = 1
	si.posting_date = args.posting_date or nowdate()

	si.company = args.company or "_Test Company"
	si.customer = args.customer or "_Test Customer"
	si.debit_to = args.debit_to or "Debtors - _TC"
	si.update_stock = args.update_stock
	si.is_pos = args.is_pos
	si.is_return = args.is_return
	si.return_against = args.return_against
	si.currency = args.currency or "INR"
	si.conversion_rate = args.conversion_rate or 1
	si.naming_series = args.naming_series or "T-SINV-"
	si.cost_center = args.parent_cost_center

	bundle_id = None
	if si.update_stock and (args.get("batch_no") or args.get("serial_no")):
		batches = {}
		qty = args.qty or 1
		item_code = args.item or args.item_code or "_Test Item"
		if args.get("batch_no"):
			batches = frappe._dict({args.batch_no: qty})

		serial_nos = args.get("serial_no") or []

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item_code,
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
					"qty": qty,
					"batches": batches,
					"voucher_type": "Sales Invoice",
					"serial_nos": serial_nos,
					"type_of_transaction": "Outward" if not args.is_return else "Inward",
					"posting_date": si.posting_date or today(),
					"posting_time": si.posting_time,
					"do_not_submit": True,
				}
			)
		).name

	si.append(
		"items",
		{
			"item_code": args.item or args.item_code or "_Test Item",
			"item_name": args.item_name or "_Test Item",
			"description": args.description or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"target_warehouse": args.target_warehouse,
			"qty": args.qty or 1,
			"uom": args.uom or "Nos",
			"stock_uom": args.uom or "Nos",
			"rate": args.rate if args.get("rate") is not None else 100,
			"price_list_rate": args.price_list_rate if args.get("price_list_rate") is not None else 100,
			"income_account": args.income_account or "Sales - _TC",
			"expense_account": args.expense_account or "Cost of Goods Sold - _TC",
			"discount_account": args.discount_account or None,
			"discount_amount": args.discount_amount or 0,
			"asset": args.asset or None,
			"cost_center": args.cost_center or "_Test Cost Center - _TC",
			"conversion_factor": args.get("conversion_factor", 1),
			"incoming_rate": args.incoming_rate or 0,
			"serial_and_batch_bundle": bundle_id,
		},
	)

	if not args.do_not_save:
		si.insert()
		if not args.do_not_submit:
			si.submit()
		else:
			si.payment_schedule = []

		si.load_from_db()
	else:
		si.payment_schedule = []

	return si


def create_sales_invoice_against_cost_center(**args):
	si = frappe.new_doc("Sales Invoice")
	args = frappe._dict(args)
	if args.posting_date:
		si.set_posting_time = 1
	si.posting_date = args.posting_date or nowdate()

	si.company = args.company or "_Test Company"
	si.cost_center = args.cost_center or "_Test Cost Center - _TC"
	si.customer = args.customer or "_Test Customer"
	si.debit_to = args.debit_to or "Debtors - _TC"
	si.update_stock = args.update_stock
	si.is_pos = args.is_pos
	si.is_return = args.is_return
	si.return_against = args.return_against
	si.currency = args.currency or "INR"
	si.conversion_rate = args.conversion_rate or 1

	si.append(
		"items",
		{
			"item_code": args.item or args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty or 1,
			"rate": args.rate or 100,
			"income_account": "Sales - _TC",
			"expense_account": "Cost of Goods Sold - _TC",
			"cost_center": args.cost_center or "_Test Cost Center - _TC",
		},
	)

	if not args.do_not_save:
		si.insert()
		if not args.do_not_submit:
			si.submit()
		else:
			si.payment_schedule = []
	else:
		si.payment_schedule = []

	return si


test_dependencies = ["Journal Entry", "Contact", "Address"]
test_records = frappe.get_test_records("Sales Invoice")


def get_outstanding_amount(against_voucher_type, against_voucher, account, party, party_type):
	bal = flt(
		frappe.db.sql(
			"""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s and against_voucher=%s
		and account = %s and party = %s and party_type = %s""",
			(against_voucher_type, against_voucher, account, party, party_type),
		)[0][0]
		or 0.0
	)

	if against_voucher_type == "Purchase Invoice":
		bal = bal * -1

	return bal


def get_taxes_and_charges():
	return [
		{
			"account_head": "_Test Account Excise Duty - TCP1",
			"charge_type": "On Net Total",
			"cost_center": "Main - TCP1",
			"description": "Excise Duty",
			"doctype": "Sales Taxes and Charges",
			"idx": 1,
			"included_in_print_rate": 1,
			"parentfield": "taxes",
			"rate": 12,
		},
		{
			"account_head": "_Test Account Education Cess - TCP1",
			"charge_type": "On Previous Row Amount",
			"cost_center": "Main - TCP1",
			"description": "Education Cess",
			"doctype": "Sales Taxes and Charges",
			"idx": 2,
			"included_in_print_rate": 1,
			"parentfield": "taxes",
			"rate": 2,
			"row_id": 1,
		},
	]


def create_internal_parties():
	from erpnext.selling.doctype.customer.test_customer import create_internal_customer

	create_internal_customer(
		customer_name="_Test Internal Customer",
		represents_company="_Test Company 1",
		allowed_to_interact_with="Wind Power LLC",
	)

	create_internal_customer(
		customer_name="_Test Internal Customer 2",
		represents_company="_Test Company with perpetual inventory",
		allowed_to_interact_with="_Test Company with perpetual inventory",
	)

	create_internal_customer(
		customer_name="_Test Internal Customer 3",
		represents_company="_Test Company",
		allowed_to_interact_with="_Test Company",
	)

	account = create_account(
		account_name="Unrealized Profit",
		parent_account="Current Liabilities - _TC",
		company="_Test Company",
	)

	frappe.db.set_value("Company", "_Test Company", "unrealized_profit_loss_account", account)

	create_internal_supplier(
		supplier_name="_Test Internal Supplier",
		represents_company="Wind Power LLC",
		allowed_to_interact_with="_Test Company 1",
	)

	create_internal_supplier(
		supplier_name="_Test Internal Supplier 2",
		represents_company="_Test Company with perpetual inventory",
		allowed_to_interact_with="_Test Company with perpetual inventory",
	)


def create_internal_supplier(supplier_name, represents_company, allowed_to_interact_with):
	if not frappe.db.exists("Supplier", supplier_name):
		supplier = frappe.get_doc(
			{
				"supplier_group": "_Test Supplier Group",
				"supplier_name": supplier_name,
				"doctype": "Supplier",
				"is_internal_supplier": 1,
				"represents_company": represents_company,
			}
		)

		supplier.append("companies", {"company": allowed_to_interact_with})
		supplier.insert()
		supplier_name = supplier.name
	else:
		supplier_name = frappe.db.exists("Supplier", supplier_name)

	return supplier_name


def setup_accounts():
	## Create internal transfer account
	account = create_account(
		account_name="Unrealized Profit",
		parent_account="Current Liabilities - TCP1",
		company="_Test Company with perpetual inventory",
	)

	frappe.db.set_value(
		"Company", "_Test Company with perpetual inventory", "unrealized_profit_loss_account", account
	)


def add_taxes(doc):
	doc.append(
		"taxes",
		{
			"account_head": "_Test Account Excise Duty - TCP1",
			"charge_type": "On Net Total",
			"cost_center": "Main - TCP1",
			"description": "Excise Duty",
			"rate": 12,
		},
	)
