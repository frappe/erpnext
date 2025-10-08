# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
import json

import frappe
from frappe import qb
from frappe.model.dynamic_links import get_dynamic_link_map
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed
from frappe.utils import add_days, flt, format_date, getdate, nowdate, today

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import (
	set_default_account_for_mode_of_payment,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import WarehouseMissingError
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	unlink_payment_on_cancel_of_invoice,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	make_inter_company_purchase_invoice,
	make_inter_company_transaction,
)
from erpnext.accounts.utils import PaymentEntryUnlinkError
from erpnext.controllers.accounts_controller import InvalidQtyError, update_invoice_status
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
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
)
from erpnext.stock.get_item_details import get_item_tax_map
from erpnext.stock.utils import get_incoming_rate, get_stock_balance


class TestSalesInvoice(FrappeTestCase):
	def setUp(self):
		from erpnext.stock.doctype.stock_ledger_entry.test_stock_ledger_entry import create_items

		create_items(["_Test Internal Transfer Item"], uoms=[{"uom": "Box", "conversion_factor": 10}])
		create_internal_parties()
		setup_accounts()
		mode_of_payment = frappe.get_doc("Mode of Payment", "Bank Draft")
		set_default_account_for_mode_of_payment(mode_of_payment, "_Test Company", "_Test Bank - _TC")
		set_default_account_for_mode_of_payment(
			mode_of_payment, "_Test Company with perpetual inventory", "_Test Bank - TCP1"
		)
		frappe.db.set_single_value("Accounts Settings", "acc_frozen_upto", None)

	@change_settings(
		"Accounts Settings",
		{"maintain_same_internal_transaction_rate": 1, "maintain_same_rate_action": "Stop"},
	)
	def test_invalid_rate_without_override(self):
		from frappe import ValidationError

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice

		si = create_sales_invoice(
			customer="_Test Internal Customer 3", company="_Test Company", is_internal_customer=1, rate=100
		)
		pi = make_inter_company_purchase_invoice(si.name)
		pi.items[0].rate = 120

		with self.assertRaises(ValidationError) as e:
			pi.insert()
			pi.submit()
		self.assertIn("Rate must be same", str(e.exception))

	def tearDown(self):
		frappe.db.rollback()
		if frappe.db.get_single_value("Selling Settings", "validate_selling_price"):
			frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)

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

	def test_sales_invoice_qty(self):
		si = create_sales_invoice(qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			si.save()

		# No error with qty=1
		si.items[0].qty = 1
		si.save()
		self.assertEqual(si.items[0].qty, 1)

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
		pe.insert(ignore_permissions=True)
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
		self.assertEqual(si.items[0].net_amount, 3947.37)
		self.assertEqual(si.net_total, si.base_net_total)
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
				499.98,
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
				750,
			],
		}

		# check if children are saved
		self.assertEqual(len(si.get("items")), len(expected_values) - 1)

		# check if item values are calculated
		for d in si.get("items"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEqual(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEqual(si.base_net_total, si.net_total)
		self.assertEqual(si.net_total, 1249.98)
		self.assertEqual(si.total, 1578.3)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Excise Duty - _TC": [140, 1389.98],
			"_Test Account Education Cess - _TC": [2.8, 1392.78],
			"_Test Account S&H Education Cess - _TC": [1.4, 1394.18],
			"_Test Account CST - _TC": [27.88, 1422.06],
			"_Test Account VAT - _TC": [156.25, 1578.31],
			"_Test Account Customs Duty - _TC": [125, 1703.31],
			"_Test Account Shipping Charges - _TC": [100, 1803.31],
			"_Test Account Discount - _TC": [-180.33, 1622.98],
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
				"net_amount": 590.05,
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
		# no rounding adjustment as the Smallest Currency Fraction Value of USD is 0.01
		if frappe.db.get_value("Currency", "USD", "smallest_currency_fraction_value") < 0.01:
			self.assertEqual(si.rounding_adjustment, 0.10)
			self.assertEqual(si.base_rounding_adjustment, 5.0)
		else:
			self.assertEqual(si.rounding_adjustment, 0.0)
			self.assertEqual(si.base_rounding_adjustment, 0.0)

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
		pe.insert(ignore_permissions=True)
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

		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 50})
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 50})

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

		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 500})
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 500})
		pos.insert()
		pos.submit()

		pos_return = make_sales_return(pos.name)

		pos_return.insert()
		pos_return.submit()

		self.assertEqual(pos_return.get("payments")[0].amount, -500)
		self.assertEqual(pos_return.get("payments")[1].amount, -500)

	def validate_ledger_entries(self, payment_entries, sales_invoices):
		"""
		Validate GL entries for the given payment entries and sales invoices.
		- payment_entries: A list of Payment Entry objects.
		- sales_invoices: A list of Sales Invoice objects.
		"""
		# Collect all ledger entries related to the payment entries
		ledger_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": ["in", [pe.name for pe in payment_entries]]},
			fields=["account", "debit", "credit"],
		)

		# Collect the total credit amounts for Debtors account
		debtor_account_credits = {}
		for entry in ledger_entries:
			if entry["account"] not in debtor_account_credits:
				debtor_account_credits[entry["account"]] = 0
			debtor_account_credits[entry["account"]] += entry["credit"]

		# Validate debit entries for each Payment Entry (Bank account)
		for pe in payment_entries:
			debit_account = pe.paid_to  # Bank account
			debit_amount = pe.paid_amount
			assert any(
				entry["account"] == debit_account and entry["debit"] == debit_amount
				for entry in ledger_entries
			), f"Debit entry missing for account: {debit_account} with amount: {debit_amount}"

		# Validate credit entries for the receivable accounts of each Sales Invoice (Debtors account)
		for si in sales_invoices:
			total_credit = sum(
				pe.paid_amount
				for pe in payment_entries
				if any(
					ref.reference_doctype == "Sales Invoice" and ref.reference_name == si.name
					for ref in pe.references
				)
			)

			# Get the total credit for the Debtors account associated with the Sales Invoice
			credit_account = si.debit_to  # Debtors account
			total_ledger_credit = debtor_account_credits.get(credit_account, 0)

			# Assert that the total credit matches the calculated total credit
			assert total_ledger_credit == total_credit, (
				f"Total credit for Debtors account: {credit_account} should be equal to the total paid amount. "
				f"Total Ledger Credit: {total_ledger_credit}, Total Paid: {total_credit}"
			)

	def test_sales_invoice_payment(self):
		"""Test payment against a single Sales Invoice."""
		today = nowdate()

		# Step 1: Create and Submit Sales Invoice
		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item="_Test Item",
			qty=1,
			rate=100,
			warehouse="_Test Warehouse - _TC",
			currency="INR",
			naming_series="T-SINV-",
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		# Step 2: Create Payment Entry
		payment_entry = get_payment_entry("Sales Invoice", sales_invoice.name, bank_account="Cash - _TC")
		payment_entry.reference_no = f"Test-{sales_invoice.name}"
		payment_entry.reference_date = today
		payment_entry.paid_from_account_currency = sales_invoice.currency
		payment_entry.paid_to_account_currency = sales_invoice.currency
		payment_entry.source_exchange_rate = 1
		payment_entry.target_exchange_rate = 1
		payment_entry.paid_amount = sales_invoice.grand_total

		payment_entry.insert()
		payment_entry.submit()

		# Step 3: Validate Outstanding Amount
		sales_invoice.reload()
		self.assertEqual(sales_invoice.outstanding_amount, 0, "Outstanding amount is not zero.")
		self.assertEqual(sales_invoice.status, "Paid", "Sales Invoice status is not 'Paid'.")

		# Step 4: Validate Ledger Entries
		self.validate_ledger_entries(payment_entries=[payment_entry], sales_invoices=[sales_invoice])

	def test_single_payment_multiple_sales_invoices(self):
		# Step 1: Create multiple Sales Invoices
		sales_invoice1 = create_sales_invoice()
		sales_invoice2 = create_sales_invoice()
		total_payment_amount = sales_invoice1.grand_total + sales_invoice2.grand_total

		# Step 3: Create Payment Entry and allocate payment to both invoices
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		payment_entry = get_payment_entry(
			"Sales Invoice", sales_invoice1.name, bank_account="_Test Bank - _TC"
		)
		payment_entry.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": sales_invoice2.name,
				"allocated_amount": sales_invoice2.grand_total,
			},
		)
		payment_entry.reference_no = f"Test-{sales_invoice1.name}-{sales_invoice2.name}"
		payment_entry.reference_date = nowdate()
		payment_entry.paid_from_account_currency = sales_invoice1.currency
		payment_entry.paid_to_account_currency = sales_invoice1.currency
		payment_entry.source_exchange_rate = 1
		payment_entry.target_exchange_rate = 1
		payment_entry.paid_amount = total_payment_amount

		payment_entry.insert()
		payment_entry.submit()

		# Step 4: Reload Sales Invoices to get updated data
		sales_invoice1.reload()
		sales_invoice2.reload()

		# Step 5: Assertions for Sales Invoices
		for si in [sales_invoice1, sales_invoice2]:
			self.assertEqual(si.outstanding_amount, 0)
			self.assertEqual(si.status, "Paid")

		# Step 6: Validate Ledger Entries
		self.validate_ledger_entries(
			payment_entries=[payment_entry], sales_invoices=[sales_invoice1, sales_invoice2]
		)

	def test_multiple_payment_entries_single_sales_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

		today = nowdate()

		# Step 1: Create and Submit Sales Invoice without payment schedule
		si = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item="_Test Item",
			qty=1,
			rate=300,
			warehouse="_Test Warehouse - _TC",
			currency="INR",
			naming_series="T-SINV-",
		)
		si.submit()

		# Step 2: Test - No Payments Yet
		self.assertEqual(si.status, "Unpaid")

		# Step 3: Create Payment Entry 1 with less than the due amount
		pe1 = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe1.reference_no = "PE1-001"
		pe1.reference_date = today
		pe1.paid_amount = 1  # Less than the total due
		pe1.references[0].allocated_amount = pe1.paid_amount  # Allocate 1 as the paid amount
		pe1.submit()

		# After Payment Entry 1: Sales Invoice should still be Overdue
		si.reload()
		self.assertEqual(si.status, "Partly Paid")

		# Step 4: Create Payment Entry 2 (Partly Paid - 50% of grand total)
		pe2 = frappe.copy_doc(pe1)  # Copy of Payment Entry 1 for simplicity
		pe2.paid_amount = si.grand_total / 2  # Pay 50% of the total amount
		pe2.references[0].allocated_amount = pe2.paid_amount  # Allocate the paid amount
		pe2.submit()

		# After Payment Entry 2: Sales Invoice should be Partly Paid
		si.reload()
		self.assertEqual(si.status, "Partly Paid")

		# Step 5: Create Payment Entry 3 (Fully Paid)
		pe3 = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe3.reference_no = "PE3-001"
		pe3.reference_date = today
		pe3.paid_amount = si.outstanding_amount  # Pay the remaining outstanding amount
		pe3.references[0].allocated_amount = pe3.paid_amount  # Allocate the remaining amount
		pe3.submit()

		# After Payment Entry 3: Sales Invoice should be Paid
		si.reload()
		self.assertEqual(si.status, "Paid")

		# Step 6: Validate Ledger Entries (You can include additional checks to validate the ledger entries if necessary)
		self.validate_ledger_entries(payment_entries=[pe1, pe2, pe3], sales_invoices=[si])

	def test_multiple_invoices_multiple_payments(self):
		"""Test payments against multiple Sales Invoices and validate ledger entries."""
		today = nowdate()

		# Step 1: Create and Submit Sales Invoices and Payment Entries
		sales_invoices, payment_entries = [], []
		for i in range(3):
			si = create_sales_invoice(
				customer="_Test Customer",
				company="_Test Company",
				item="_Test Item",
				qty=1,
				rate=100,
				warehouse="_Test Warehouse - _TC",
				currency="INR",
				naming_series=f"T-SINV-{i+1}-",
			)
			sales_invoices.append(si)
			from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry

			pe = get_payment_entry("Sales Invoice", si.name, bank_account="Cash - _TC")
			pe.update(
				{
					"reference_no": f"Test-{si.name}",
					"reference_date": today,
					"paid_from_account_currency": si.currency,
					"paid_to_account_currency": si.currency,
					"source_exchange_rate": 1,
					"target_exchange_rate": 1,
					"paid_amount": si.grand_total,
				}
			)
			pe.insert(ignore_permissions=True)
			pe.submit()
			payment_entries.append(pe)

		# Step 2: Validate Outstanding Amounts and Ledger Entries
		for si in sales_invoices:
			si.reload()
			self.assertEqual(si.outstanding_amount, 0, f"Outstanding amount is not zero for {si.name}.")
			self.assertEqual(si.status, "Paid", f"Sales Invoice status is not 'Paid' for {si.name}.")

		# Step 3: Validate Ledger Entries
		ledger_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": ["in", [pe.name for pe in payment_entries]]},
			fields=["account", "debit", "credit"],
		)
		for pe in payment_entries:
			debit_account, debit_amount = pe.paid_to, pe.paid_amount
			credit_account = sales_invoices[0].debit_to if pe.party_type == "Customer" else pe.paid_from
			credit_amount = pe.paid_amount

			# Assert debit entry for Cash/Bank and credit entry for Debtors/Creditors
			assert any(
				entry["account"] == debit_account and entry["debit"] == debit_amount
				for entry in ledger_entries
			), f"Debit entry missing for account: {debit_account} with amount: {debit_amount}."
			assert any(
				entry["account"] == credit_account and entry["credit"] == credit_amount
				for entry in ledger_entries
			), f"Credit entry missing for account: {credit_account} with amount: {credit_amount}."

		# Step 4: Validate total debit and credit balance
		sum(pe.paid_amount for pe in payment_entries)
		total_debit = sum(entry["debit"] for entry in ledger_entries if entry["account"] == debit_account)
		total_credit = sum(entry["credit"] for entry in ledger_entries if entry["account"] == credit_account)
		assert (
			total_debit == total_credit
		), f"Total debit ({total_debit}) does not match total credit ({total_credit})."

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

		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 50})
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 60})

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

		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 50})
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 40})

		pos.write_off_outstanding_amount_automatically = 1
		pos.insert()
		pos.submit()

		self.assertEqual(pos.grand_total, 100.0)
		self.assertEqual(pos.write_off_amount, 10)

	def test_ledger_entries_of_return_pos_invoice(self):
		make_pos_profile()

		pos = create_sales_invoice(do_not_save=True)
		pos.is_pos = 1
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 100})
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
		expected_list = list(expected)
		res = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pos_return.name, "is_cancelled": 0},
			fields=["account", "debit", "credit", "voucher_no", "against_voucher"],
			order_by="account, debit, credit",
			as_list=1,
		)
		self.assertEqual(expected_list, res)

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

		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 50})
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 60})

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
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

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
		from erpnext.stock.doctype.stock_entry.test_stock_entry import (
			get_qty_after_transaction,
			make_stock_entry,
		)

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
		pe.insert(ignore_permissions=True)
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
		self.assertEqual(sales_order.advance_paid, 300.0)

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
		for rate in [400.25, 600.30, 100.65]:
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
		self.assertEqual(si.net_total, si.base_net_total)
		self.assertEqual(si.net_total, 1272.20)
		self.assertEqual(si.grand_total, 1501.20)
		self.assertEqual(si.total_taxes_and_charges, 229)
		self.assertEqual(si.rounding_adjustment, -0.20)

		round_off_account = frappe.get_cached_value("Company", "_Test Company", "round_off_account")
		expected_values = {
			"_Test Account Service Tax - _TC": [0.0, 114.50],
			"_Test Account VAT - _TC": [0.0, 114.50],
			si.debit_to: [1501, 0.0],
			round_off_account: [0.20, 0.0],
			"Sales - _TC": [0.0, 1272.20],
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

	@if_app_installed("assets")
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
		self.assertEqual(si.net_total, si.base_net_total)
		self.assertEqual(si.net_total, 4007.15)
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
				[round_off_account, 0.01, 0.0],
			]
		)

		gl_entries = frappe.db.sql(
			"""select account, sum(debit) as debit, sum(credit) as credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			group by account
			order by account desc""",
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
		pe.insert(ignore_permissions=True)
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

	def test_validate_inter_company_transaction_address_links(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		def _validate_address_link(address, link_doctype, link_name):
			return frappe.db.get_value(
				"Dynamic Link",
				{
					"parent": address,
					"parenttype": "Address",
					"link_doctype": link_doctype,
					"link_name": link_name,
				},
				"parent",
			)

		create_company(company_name="Wind Power LLC", country="United States", currency="USD", abbr="WP")
		get_customer = frappe.get_doc("Customer", "_Test Internal Customer")
		get_customer.is_internal_customer = 1
		get_customer.represents_company = "_Test Company 1"
		get_customer.append("companies", {"company": "Wind Power LLC"})
		get_customer.save()
		get_or_create_fiscal_year("Wind Power LLC")
		args = {
			"supplier_name": "Test Intercompany Supplier" + frappe.generate_hash(length=3),
			"default_currency": "USD",
		}
		supplier = create_supplier(**args)
		supplier.is_internal_supplier = 1
		supplier.represents_company = "Wind Power LLC"
		supplier.save()
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
		target_doc.save()

		if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
			for details in [
				("supplier_address", "Supplier", target_doc.supplier),
				("dispatch_address", "Company", target_doc.company),
				("shipping_address", "Company", target_doc.company),
				("billing_address", "Company", target_doc.company),
			]:
				if address := target_doc.get(details[0]):
					self.assertEqual(address, _validate_address_link(address, details[1], details[2]))
		else:
			for details in [
				("company_address", "Company", target_doc.company),
				("shipping_address_name", "Customer", target_doc.customer),
				("customer_address", "Customer", target_doc.customer),
			]:
				if address := target_doc.get(details[0]):
					self.assertEqual(address, _validate_address_link(address, details[1], details[2]))

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
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

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
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

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
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
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
		item_tax_map = get_item_tax_map(
			company=sales_invoice.company,
			item_tax_template=sales_invoice.items[0].item_tax_template,
		)
		self.assertEqual(sales_invoice.items[0].item_tax_template, "_Test Account Excise Duty @ 12 - _TC")
		self.assertEqual(sales_invoice.items[0].item_tax_rate, item_tax_map)

		# Apply discount
		sales_invoice.apply_discount_on = "Net Total"
		sales_invoice.discount_amount = 300
		sales_invoice.save()

		item_tax_map = get_item_tax_map(
			company=sales_invoice.company,
			item_tax_template=sales_invoice.items[0].item_tax_template,
		)
		self.assertEqual(sales_invoice.items[0].item_tax_template, "_Test Account Excise Duty @ 10 - _TC")
		self.assertEqual(sales_invoice.items[0].item_tax_rate, item_tax_map)

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
		create_party_link("Supplier", supplier, customer)

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

	def test_total_billed_amount(self):
		si = create_sales_invoice(do_not_submit=True)
		project = frappe.new_doc("Project")
		project.company = "_Test Company"
		project.project_name = "Test Total Billed Amount"
		project.save()
		si.project = project.name
		si.save()
		si.submit()
		doc = frappe.get_doc("Project", project.name)
		self.assertEqual(doc.total_billed_amount, si.grand_total)

	def test_total_billed_amount_with_different_projects(self):
		# This test case is for checking the scenario where project is set at document level and for **some** child items only, not all
		from copy import copy

		si = create_sales_invoice(do_not_submit=True)

		project = frappe.new_doc("Project")
		project.company = "_Test Company"
		project.project_name = "Test Total Billed Amount"
		project.save()

		si.project = project.name
		si.items.append(copy(si.items[0]))
		si.items.append(copy(si.items[0]))
		si.items[0].project = project.name
		si.items[1].project = project.name
		# Not setting project on last item
		si.items[1].insert()
		si.items[2].insert()
		si.submit()

		project.reload()
		self.assertIsNone(si.items[2].project)
		self.assertEqual(project.total_billed_amount, 300)

		# party_link.delete()
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

	@if_app_installed("sales_commission")
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

	@if_app_installed("india_compliance")
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
		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 500})
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 500})
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

	def test_gl_voucher_subtype(self):
		si = create_sales_invoice()
		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": si.name},
			pluck="voucher_subtype",
		)
		self.assertTrue(all([x == "Sales Invoice" for x in gl_entries]))
		si = create_sales_invoice(is_return=1, qty=-1)
		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": si.name},
			pluck="voucher_subtype",
		)
		self.assertTrue(all([x == "Credit Note" for x in gl_entries]))

	def test_validation_on_opening_invoice_with_rounding(self):
		si = create_sales_invoice(qty=1, rate=99.98, do_not_submit=True)
		si.is_opening = "Yes"
		si.items[0].income_account = "Temporary Opening - _TC"
		si.save()
		self.assertRaises(frappe.ValidationError, si.submit)

	def _create_opening_roundoff_account(self, company_name):
		liability_root = frappe.db.get_all(
			"Account",
			filters={"company": company_name, "root_type": "Liability", "disabled": 0},
			order_by="lft",
			limit=1,
		)[0]
		# setup round off account
		if acc := frappe.db.exists(
			"Account",
			{
				"account_name": "Round Off for Opening",
				"account_type": "Round Off for Opening",
				"company": company_name,
			},
		):
			frappe.db.set_value("Company", company_name, "round_off_for_opening", acc)
		else:
			acc = frappe.new_doc("Account")
			acc.company = company_name
			acc.parent_account = liability_root.name
			acc.account_name = "Round Off for Opening"
			acc.account_type = "Round Off for Opening"
			acc.save()
			frappe.db.set_value("Company", company_name, "round_off_for_opening", acc.name)

	def test_opening_invoice_with_rounding_adjustment(self):
		si = create_sales_invoice(qty=1, rate=99.98, do_not_submit=True)
		si.is_opening = "Yes"
		si.items[0].income_account = "Temporary Opening - _TC"
		si.save()
		self._create_opening_roundoff_account(si.company)
		si.reload()
		si.submit()
		res = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": si.name, "is_opening": "Yes", "is_cancelled": False},
			fields=["account", "debit", "credit", "is_opening"],
		)
		self.assertEqual(len(res), 3)

	def _create_opening_invoice_with_inclusive_tax(self):
		si = create_sales_invoice(qty=1, rate=90, do_not_submit=True)
		si.is_opening = "Yes"
		si.items[0].income_account = "Temporary Opening - _TC"
		item_template = si.items[0].as_dict()
		item_template.name = None
		item_template.rate = 55
		si.append("items", item_template)
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Testing...",
				"rate": 5,
				"included_in_print_rate": True,
			},
		)
		# there will be 0.01 precision loss between Dr and Cr
		# caused by 'included_in_print_tax' option
		si.save()
		return si

	def test_rounding_validation_for_opening_with_inclusive_tax(self):
		si = self._create_opening_invoice_with_inclusive_tax()
		# 'Round Off for Opening' not set in Company master
		# Ledger level validation must be thrown
		self.assertRaises(frappe.ValidationError, si.submit)

	def test_ledger_entries_on_opening_invoice_with_rounding_loss_by_inclusive_tax(self):
		si = self._create_opening_invoice_with_inclusive_tax()
		# 'Round Off for Opening' is set in Company master
		self._create_opening_roundoff_account(si.company)
		si.submit()
		actual = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": si.name, "is_opening": "Yes"},
			fields=["account", "debit", "credit", "is_opening"],
			order_by="account,debit",
		)
		expected = [
			{"account": "_Test Account Service Tax - _TC", "debit": 0.0, "credit": 6.9, "is_opening": "Yes"},
			{"account": "Debtors - _TC", "debit": 145.0, "credit": 0.0, "is_opening": "Yes"},
			{"account": "Round Off for Opening - _TC", "debit": 0.0, "credit": 0.01, "is_opening": "Yes"},
			{"account": "Temporary Opening - _TC", "debit": 0.0, "credit": 138.09, "is_opening": "Yes"},
		]
		self.assertEqual(len(actual), 4)
		self.assertEqual(expected, actual)

	def test_sales_invoice_without_sales_order_TC_S_006(self):
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_customer(customer_name="_Test Customer", company="_Test Company")
		item = create_item(item_code="_Test Item 1", valuation_rate=100)
		make_stock_entry(item_code="_Test Item 1", target="_Test Warehouse - _TC", qty=50, basic_rate=100)
		setting = frappe.get_doc("Selling Settings")
		setting.so_required = "No"
		setting.save()

		self.assertEqual(setting.so_required, "No")

		si = create_sales_invoice(
			cost_center="Main - _TC",
			item_code=item.name,
			selling_price_list="Standard Selling",
			income_account="Sales - _TC",
			expense_account="Cost of Goods Sold - _TC",
			debit_to="Debtors - _TC",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid", "Sales Invoice not submitted")

		si_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Sales - _TC"},
			"credit",
		)
		self.assertEqual(si_acc_credit, 15000)

		si_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Debtors - _TC"},
			"debit",
		)
		self.assertEqual(si_acc_debit, 15000)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		dn = make_delivery_note(si.name)

		dn.insert()
		dn.submit()

		self.assertEqual(dn.status, "Completed", "Delivery Note not submitted")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item 1", "voucher_no": dn.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -5)

	def test_sales_invoice_with_update_stock_checked_TC_S_007(self):
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_customer(customer_name="_Test Customer", company="_Test Company")
		item = create_item(item_code="_Test Item 1", valuation_rate=100)
		make_stock_entry(item_code="_Test Item 1", target="_Test Warehouse - _TC", qty=50, basic_rate=100)
		si = create_sales_invoice(
			cost_center="Main - _TC",
			item_code=item.name,
			selling_price_list="Standard Selling",
			income_account="Sales - _TC",
			expense_account="Cost of Goods Sold - _TC",
			debit_to="Debtors - _TC",
			qty=5,
			rate=3000,
			do_not_save=True,
		)
		si.update_stock = 1
		si.save()
		si.submit()
		self.assertEqual(si.status, "Unpaid", "Sales Invoice not submitted")

		qty_change = frappe.get_all(
			"Stock Ledger Entry",
			{"item_code": "_Test Item 1", "voucher_no": si.name, "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "valuation_rate"],
		)
		self.assertEqual(qty_change[0].get("actual_qty"), -5)

		si2_acc_credit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Sales - _TC"},
			"credit",
		)
		self.assertEqual(si2_acc_credit, 15000)

		si2_acc_debit = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": si.name, "account": "Debtors - _TC"},
			"debit",
		)
		self.assertEqual(si2_acc_debit, 15000)

	def test_jv_records_creation_diff_ex_rate_TC_ACC_029(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import get_jv_entry_account
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_cost_center(
			cost_center_name="_Test Cost Center",
			company="_Test Company",
			parent_cost_center="_Test Company - _TC",
		)

		create_account(
			account_name="_Test Receivable USD",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="USD",
			account_type="Receivable",
			roroot_type="Asset",
		)

		create_customer(
			customer_name="_Test Customer USD",
			currency="USD",
			company="_Test Company",
			account="_Test Receivable USD - _TC",
		)

		item = make_test_item(item_name="_Test Item USD")

		if item.is_new():
			item.append(
				"item_defaults",
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company",
					"selling_cost_center": "_Test Cost Center - _TC",
				},
			)
			item.save()

		si = create_sales_invoice(
			customer="_Test Customer USD",
			company="_Test Company",
			parent_cost_center="_Test Cost Center - _TC",
			conversion_rate=63,
			currency="USD",
			debit_to="_Test Receivable USD - _TC",
			item_code=item.name,
			qty=1,
			rate=100,
		)
		si.save()
		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name)
		pe.payment_type = "Receive"
		pe.mode_of_payment = "Cash"
		pe.paid_from = "_Test Receivable USD - _TC"
		pe.paid_to = "Cash - _TC"
		pe.source_exchange_rate = 60
		pe.save()
		pe.submit()

		jv_name = get_jv_entry_account(
			credit_to=si.debit_to, reference_name=si.name, party_type="Customer", party=pe.party, credit=300
		)

		self.assertEqual(
			frappe.db.get_value("Journal Entry", jv_name.parent, "voucher_type"), "Exchange Gain Or Loss"
		)

		expected_jv_entries = [
			["Exchange Gain/Loss - _TC", 300.0, 0.0, pe.posting_date],
			["_Test Receivable USD - _TC", 0.0, 300.0, pe.posting_date],
		]

		check_gl_entries(
			doc=self,
			voucher_no=jv_name.parent,
			expected_gle=expected_jv_entries,
			posting_date=pe.posting_date,
			voucher_type="Journal Entry",
		)

	def test_jv_records_creation_diff_ex_rate_TC_ACC_030(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_payment_entry,
			make_test_item,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import get_jv_entry_account
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company(company_name="_Test Company 3", country="India", currency="INR", abbr="_TC5")
		get_or_create_fiscal_year("_Test Company 3")
		create_cost_center(
			cost_center_name="_Test Cost Center",
			company="_Test Company 3",
			parent_cost_center="_Test Company 3 - _TC3",
		)

		create_account(
			account_name="_Test Receivable USD",
			parent_account="Current Assets - _TC3",
			company="_Test Company 3",
			account_currency="USD",
			account_type="Receivable",
		)
		create_account(
			account_name="_Test Cash",
			parent_account="Cash In Hand - _TC3",
			company="_Test Company 3",
			account_currency="INR",
			account_type="Cash",
		)

		create_customer(
			customer_name="_Test Customer USD",
			currency="USD",
			company="_Test Company 3",
			account="_Test Receivable USD - _TC3",
		)

		item = make_test_item(item_name="_Test Item USD")

		if item.is_new():
			item.append(
				"item_defaults",
				{
					"default_warehouse": "_Test Warehouse - _TC5",
					"company": "_Test Company",
					"selling_cost_center": "_Test Cost Center - _TC5",
				},
			)
			item.save()

		customer = frappe.get_doc("Customer", "_Test Customer USD")

		if customer:
			pe = create_payment_entry(
				party_type="Customer",
				party=customer.name,
				company="_Test Company 3",
				payment_type="Receive",
				paid_from="_Test Receivable USD - _TC3",
				paid_to="_Test Cash - _TC3",
				paid_amount=100,
				save=True,
			)
			pe.source_exchange_rate = 60
			pe.received_amount = 6000
			pe.save()
			pe.submit()

			si = create_sales_invoice(
				customer="_Test Customer USD",
				company="_Test Company 3",
				parent_cost_center="_Test Cost Center - _TC3",
				cost_center="_Test Cost Center - _TC3",
				conversion_rate=63,
				currency="USD",
				debit_to="_Test Receivable USD - _TC3",
				income_account="Sales - _TC3",
				expense_account="Cost of Goods Sold - _TC3",
				item_code=item.name,
				qty=1,
				rate=120,
				do_not_submit=True,
			)
			si.append(
				"advances",
				{
					"reference_type": "Payment Entry",
					"reference_name": pe.name,
					"advance_amount": 100,
					"allocated_amount": 100,
					"ref_exchange_rate": 60,
				},
			)
			si.save()
			si.submit()

			jv_name = get_jv_entry_account(
				credit_to=si.debit_to,
				reference_name=si.name,
				party_type="Customer",
				party=pe.party,
				credit=300,
			)

			self.assertEqual(
				frappe.db.get_value("Journal Entry", jv_name.parent, "voucher_type"), "Exchange Gain Or Loss"
			)

			expected_jv_entries = [
				["Exchange Gain/Loss - _TC3", 300.0, 0.0, pe.posting_date],
				["_Test Receivable USD - _TC3", 0.0, 300.0, pe.posting_date],
			]

			check_gl_entries(
				doc=self,
				voucher_no=jv_name.parent,
				expected_gle=expected_jv_entries,
				posting_date=pe.posting_date,
				voucher_type="Journal Entry",
			)

	def test_single_payment_request_for_purchase_invoice_TC_ACC_037(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		setup_bank_accounts()

		create_cost_center(
			cost_center_name="_Test Cost Center",
			company="_Test Company",
			parent_cost_center="_Test Company - _TC",
		)

		create_account(
			account_name="_Test Receivable",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Receivable",
		)
		create_account(
			account_name="_Test Cash",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Cash",
		)

		create_customer(
			customer_name="_Test Customer",
			currency="INR",
			company="_Test Company",
			account="_Test Receivable - _TC",
		)

		item = make_test_item(item_name="_Test Item")

		if item.is_new():
			item.append(
				"item_defaults",
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company",
					"selling_cost_center": "_Test Cost Center - _TC",
				},
			)
			item.save()

		customer = frappe.get_doc("Customer", "_Test Customer")

		if customer:
			si = create_sales_invoice(
				customer="_Test Customer",
				company="_Test Company",
				parent_cost_center="_Test Cost Center - _TC",
				item_code=item.name,
				qty=1,
				rate=5000,
			)

			si.submit()

			pr = make_payment_request(
				dt="Sales Invoice",
				dn=si.name,
				recipient_id="test@test.com",
				payment_gateway_account="_Test Gateway - INR",
				mute_email=1,
				submit_doc=1,
				return_doc=1,
			)

			pe = pr.set_as_paid()
			pe.save()
			pe.submit()
			pr.load_from_db()
			self.assertEqual(pr.status, "Paid")
			si.load_from_db()
			self.assertEqual(si.status, "Paid")
			expected_gle = [
				["Debtors - _TC", 0.0, si.grand_total, pe.posting_date],
				["_Test Bank - _TC", si.grand_total, 0.0, pe.posting_date],
			]
			check_gl_entries(
				doc=self,
				voucher_no=pe.name,
				expected_gle=expected_gle,
				voucher_type="Payment Entry",
				posting_date=pe.posting_date,
			)

	def test_multiple_payment_request_for_purchase_invoice_TC_ACC_038(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		setup_bank_accounts()

		create_cost_center(
			cost_center_name="_Test Cost Center",
			company="_Test Company",
			parent_cost_center="_Test Company - _TC",
		)

		create_account(
			account_name="_Test Receivable",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Receivable",
		)
		create_account(
			account_name="_Test Cash",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Cash",
		)

		create_customer(
			customer_name="_Test Customer",
			currency="INR",
			company="_Test Company",
			account="_Test Receivable - _TC",
		)

		item = make_test_item(item_name="_Test Item")

		if item.is_new():
			item.append(
				"item_defaults",
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company",
					"selling_cost_center": "_Test Cost Center - _TC",
				},
			)
			item.save()

		customer = frappe.get_doc("Customer", "_Test Customer")

		if customer:
			si = create_sales_invoice(
				customer="_Test Customer",
				company="_Test Company",
				parent_cost_center="_Test Cost Center - _TC",
				item_code=item.name,
				qty=1,
				rate=5000,
			)

			si.submit()

			pr = make_payment_request(
				dt="Sales Invoice",
				dn=si.name,
				recipient_id="test@test.com",
				payment_gateway_account="_Test Gateway - INR",
				mute_email=1,
				return_doc=1,
			)
			pr.grand_total = pr.grand_total / 2
			pr.save()
			pr.submit()
			pe = pr.set_as_paid()
			pe.save()
			pe.submit()

			pr.load_from_db()
			self.assertEqual(pr.status, "Paid")
			si.load_from_db()
			self.assertEqual(si.status, "Partly Paid")
			expected_gle = [
				["Debtors - _TC", 0.0, si.grand_total / 2, pe.posting_date],
				["_Test Bank - _TC", si.grand_total / 2, 0.0, pe.posting_date],
			]
			check_gl_entries(
				doc=self,
				voucher_no=pe.name,
				expected_gle=expected_gle,
				voucher_type="Payment Entry",
				posting_date=pe.posting_date,
			)
			_pr = make_payment_request(
				dt="Sales Invoice",
				dn=si.name,
				recipient_id="test@test.com",
				payment_gateway_account="_Test Gateway - INR",
				mute_email=1,
				return_doc=1,
				submit_doc=1,
			)
			_pe = _pr.set_as_paid()
			_pe.save()
			_pe.submit()

			_pr.load_from_db()
			self.assertEqual(_pr.status, "Paid")
			si.load_from_db()
			self.assertEqual(si.status, "Paid")
			expected_gle = [
				["Debtors - _TC", 0.0, si.grand_total / 2, _pe.posting_date],
				["_Test Bank - _TC", si.grand_total / 2, 0.0, _pe.posting_date],
			]
			check_gl_entries(
				doc=self,
				voucher_no=_pe.name,
				expected_gle=expected_gle,
				voucher_type="Payment Entry",
				posting_date=pe.posting_date,
			)

	@if_app_installed("india_compliance")
	def test_sales_invoice_without_sales_order_with_gst_TC_S_016(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_registered_company()
		get_or_create_fiscal_year("_Test Indian Registered Company")
		if not frappe.db.exists("Warehouse", "Stores - _TIRC"):
			create_warehouse("Stores - _TIRC", company="_Test Indian Registered Company")
		create_item(
			item_code="_Test Item", company="_Test Indian Registered Company", warehouse="Stores - _TIRC"
		)
		setting = frappe.get_doc("Selling Settings")
		setting.so_required = "No"
		setting.save()
		item = frappe.get_doc("Item", "_Test Item")
		item.is_stock_item = 1
		item.save()
		self.assertEqual(setting.so_required, "No")
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="Stores - _TIRC")

		company = frappe.get_all(
			"Company", {"name": "_Test Indian Registered Company"}, ["gstin", "gst_category"]
		)
		customer = frappe.get_all(
			"Customer", {"name": "_Test Registered Customer"}, ["gstin", "gst_category"]
		)
		company_add = frappe.get_all(
			"Address", {"name": "_Test Indian Registered Company-Billing"}, ["name", "gstin", "gst_category"]
		)
		customer_add = frappe.get_all(
			"Address", {"name": "_Test Registered Customer-Billing"}, ["name", "gstin", "gst_category"]
		)

		if (
			company[0].get("gst_category") == "Registered Regular"
			and customer[0].get("gst_category") == "Registered Regular"
			and customer[0].get("gstin")
			and customer[0].get("gstin")
		):
			if (
				company_add[0].get("gst_category") == "Registered Regular"
				and customer_add[0].get("gst_category") == "Registered Regular"
				and company_add[0].get("gstin")
				and customer_add[0].get("gstin")
			):
				si = create_sales_invoice(
					company="_Test Indian Registered Company",
					customer="_Test Registered Customer",
					warehouse="Stores - _TIRC",
					cost_center="Main - _TIRC",
					selling_price_list="Standard Selling",
					income_account="Sales - _TIRC",
					expense_account="Cost of Goods Sold - _TIRC",
					debit_to="Debtors - _TIRC",
					qty=4,
					rate=5000,
					do_not_save=True,
				)
				si.tax_category = "In-State"
				si.taxes_and_charges = "Output GST In-state - _TIRC"
				si.customer_address = customer_add[0].get("name")
				si.billing_address_gstin = customer_add[0].get("gstin")
				si.company_address = company_add[0].get("name")
				si.company_gstin = company_add[0].get("gstin")
				si.save()
				si.submit()

				self.assertEqual(si.status, "Unpaid", "Sales Invoice not submitted")
				self.assertEqual(si.grand_total, si.total + si.total_taxes_and_charges)

				voucher_params = {"voucher_type": "Sales Invoice", "voucher_no": si.name}

				accounts = {
					"Sales - _TIRC": "credit",
					"Debtors - _TIRC": "debit",
					"Output Tax SGST - _TIRC": "credit",
					"Output Tax CGST - _TIRC": "credit",
				}

				gl_entries = {
					account: frappe.db.get_value("GL Entry", {**voucher_params, "account": account}, field)
					for account, field in accounts.items()
				}

				self.assertEqual(gl_entries["Sales - _TIRC"], 20000)
				self.assertEqual(gl_entries["Debtors - _TIRC"], 23600)
				self.assertEqual(gl_entries["Output Tax SGST - _TIRC"], 1800)
				self.assertEqual(gl_entries["Output Tax CGST - _TIRC"], 1800)

				from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

				dn = make_delivery_note(si.name)

				dn.insert()
				dn.submit()

				self.assertEqual(dn.status, "Completed", "Delivery Note not submitted")

				qty_change = frappe.get_all(
					"Stock Ledger Entry",
					{"item_code": "_Test Item", "voucher_no": dn.name, "warehouse": "Stores - _TIRC"},
					["actual_qty", "valuation_rate"],
				)
				self.assertEqual(qty_change[0].get("actual_qty"), -4)

				dn_acc_credit = frappe.db.get_value(
					"GL Entry",
					{
						"voucher_type": "Delivery Note",
						"voucher_no": dn.name,
						"account": "Stock In Hand - _TIRC",
					},
					"credit",
				)
				self.assertEqual(dn_acc_credit, 20000)

				dn_acc_debit = frappe.db.get_value(
					"GL Entry",
					{
						"voucher_type": "Delivery Note",
						"voucher_no": dn.name,
						"account": "Cost of Goods Sold - _TIRC",
					},
					"debit",
				)
				self.assertEqual(dn_acc_debit, 20000)

	@if_app_installed("india_compliance")
	def test_sales_invoice_with_update_stock_checked_with_gst_TC_S_017(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_registered_company()

		create_item(
			item_code="_Test Item", company="_Test Indian Registered Company", warehouse="Stores - _TIRC"
		)
		if not frappe.db.exists("Warehouse", "Stores - _TIRC"):
			create_warehouse("Stores - _TIRC", company="_Test Indian Registered Company")
		get_or_create_fiscal_year("_Test Indian Registered Company")

		company = frappe.get_all(
			"Company", {"name": "_Test Indian Registered Company"}, ["gstin", "gst_category"]
		)
		customer = frappe.get_all(
			"Customer", {"name": "_Test Registered Customer"}, ["gstin", "gst_category"]
		)
		company_add = frappe.get_all(
			"Address", {"name": "_Test Indian Registered Company-Billing"}, ["name", "gstin", "gst_category"]
		)
		customer_add = frappe.get_all(
			"Address", {"name": "_Test Registered Customer-Billing"}, ["name", "gstin", "gst_category"]
		)
		item = frappe.get_doc("Item", "_Test Item")
		item.is_stock_item = 1
		item.save()
		make_stock_entry(item_code="_Test Item", qty=10, rate=5000, target="Stores - _TIRC")

		if (
			company[0].get("gst_category") == "Registered Regular"
			and customer[0].get("gst_category") == "Registered Regular"
			and customer[0].get("gstin")
			and customer[0].get("gstin")
		):
			if (
				company_add[0].get("gst_category") == "Registered Regular"
				and customer_add[0].get("gst_category") == "Registered Regular"
				and company_add[0].get("gstin")
				and customer_add[0].get("gstin")
			):
				si = create_sales_invoice(
					company="_Test Indian Registered Company",
					customer="_Test Registered Customer",
					warehouse="Stores - _TIRC",
					cost_center="Main - _TIRC",
					selling_price_list="Standard Selling",
					income_account="Sales - _TIRC",
					expense_account="Cost of Goods Sold - _TIRC",
					debit_to="Debtors - _TIRC",
					qty=4,
					rate=5000,
					do_not_save=True,
				)
				si.tax_category = "In-State"
				si.taxes_and_charges = "Output GST In-state - _TIRC"
				si.customer_address = customer_add[0].get("name")
				si.billing_address_gstin = customer_add[0].get("gstin")
				si.company_address = company_add[0].get("name")
				si.company_gstin = company_add[0].get("gstin")
				si.update_stock = 1
				si.save()
				si.submit()

				self.assertEqual(si.status, "Unpaid", "Sales Invoice not submitted")
				self.assertEqual(si.grand_total, si.total + si.total_taxes_and_charges)

				qty_change = frappe.get_all(
					"Stock Ledger Entry",
					{"item_code": "_Test Item", "voucher_no": si.name, "warehouse": "Stores - _TIRC"},
					["actual_qty", "valuation_rate"],
				)

				if qty_change:
					actual_qty = qty_change[0].get("actual_qty")

					self.assertEqual(actual_qty, -4)
					gl_entries = frappe.db.get_all(
						"GL Entry",
						{
							"voucher_type": "Sales Invoice",
							"voucher_no": si.name,
							"account": [
								"in",
								[
									"Sales - _TIRC",
									"Debtors - _TIRC",
									"Output Tax SGST - _TIRC",
									"Output Tax CGST - _TIRC",
									"Stock In Hand - _TIRC",
									"Cost of Goods Sold - _TIRC",
								],
							],
						},
						["account", "credit", "debit"],
					)
					gl_entry_dict = {entry.account: entry for entry in gl_entries}

					self.assertEqual(gl_entry_dict.get("Sales - _TIRC", {}).get("credit", 0), 20000)
					self.assertEqual(gl_entry_dict.get("Debtors - _TIRC", {}).get("debit", 0), 23600)
					self.assertEqual(gl_entry_dict.get("Output Tax SGST - _TIRC", {}).get("credit", 0), 1800)
					self.assertEqual(gl_entry_dict.get("Output Tax CGST - _TIRC", {}).get("credit", 0), 1800)
					self.assertEqual(gl_entry_dict.get("Stock In Hand - _TIRC", {}).get("credit", 0), 20000)
					self.assertEqual(
						gl_entry_dict.get("Cost of Goods Sold - _TIRC", {}).get("debit", 0), 20000
					)

	def test_sales_invoice_and_delivery_note_with_shipping_rule_TC_S_026(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		frappe.delete_doc_if_exists("Item", "_Test Item Home Desktop 100", force=1)
		create_item(item_code="_Test Item Home Desktop 100")
		get_or_create_fiscal_year("_Test Company")
		frappe.db.set_single_value("Selling Settings", "so_required", "No")
		create_account(
			account_name="_Test Account Shipping Charges",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Chargeable",
		)
		create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")
		create_customer(customer_name="_Test Customer", company="_Test Company")

		shipping_charge = 200
		shipping = create_shipping_rule(
			shipping_rule_type="Selling", shipping_rule_name="_Test Shipping Rule"
		)

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, rate=4000)

		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			cost_center="Main - _TC",
			currency="INR",
			warehouse="Stores - _TC",
			price_list="Standard Selling",
			item_code="_Test Item Home Desktop 100",
			shipping_rule="_Test Shipping Rule",
			qty=4,
			rate=5000,
			do_not_save=1,
		)

		sales_invoice.calculate_taxes_and_totals()
		sales_invoice.submit()
		income_account = sales_invoice.items[0].income_account
		shipping_rule_account = frappe.db.get_value("Shipping Rule", "_Test Shipping Rule", "account")

		for ship in shipping.conditions:
			if ship.from_value <= 4 <= ship.to_value:
				shipping_charge = ship.shipping_amount

		expected_grand_total = 20000 + shipping_charge
		self.assertEqual(sales_invoice.grand_total, expected_grand_total)

		si_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": sales_invoice.name}, fields=["account", "debit", "credit"]
		)

		expected_si_gl = {sales_invoice.debit_to: 20200, income_account: -20000, shipping_rule_account: -200}

		for entry in si_gl_entries:
			self.assertEqual(expected_si_gl.get(entry.account, 0), entry.debit - entry.credit)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		delivery_note = make_delivery_note(sales_invoice.name)

		delivery_note.sales_invoice = sales_invoice.name
		delivery_note.save()
		delivery_note.submit()

		self.assertEqual(delivery_note.status, "Completed")

		for item in delivery_note.items:
			actual_qty = frappe.db.get_value("Bin", {"item_code": item.item_code}, "actual_qty")
			expected_qty = item.actual_qty - item.qty
			self.assertEqual(actual_qty, expected_qty)

		self.assertEqual(delivery_note.sales_invoice, sales_invoice.name)

	def test_sales_invoice_with_update_stock_and_SR_TC_S_027(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		# Set up accounts if they don't exist
		if not frappe.db.exists("Account", "Stock In Hand - _TC"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Stock In Hand",
					"parent_account": "Current Assets - _TC",
					"company": "_Test Company",
					"account_type": "Stock",
					"is_group": 0,
				}
			).insert()

		if not frappe.db.exists("Account", "Cost of Goods Sold - _TC"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Cost of Goods Sold",
					"parent_account": "Cost of Goods Sold - _TC",
					"company": "_Test Company",
					"account_type": "Cost of Goods Sold",
					"is_group": 0,
				}
			).insert()

		if not frappe.db.exists("Account", "Shipping Charges - _TC"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Shipping Charges",
					"parent_account": "Indirect Expenses - _TC",
					"company": "_Test Company",
					"account_type": "Expense Account",
					"is_group": 0,
				}
			).insert()

		# Set default accounts for test company
		frappe.set_value(
			"Company",
			"_Test Company",
			{
				"default_receivable_account": "Debtors - _TC",
				"default_income_account": "Sales - _TC",
				"default_expense_account": "Cost of Goods Sold - _TC",
				"default_inventory_account": "Stock In Hand - _TC",
			},
		)

		# Set up shipping rule account
		if not frappe.db.exists("Shipping Rule", "_Test Shipping Rule 1"):
			frappe.get_doc(
				{
					"doctype": "Shipping Rule",
					"shipping_rule_name": "_Test Shipping Rule 1",
					"label": "_Test Shipping Rule 1",
					"cost_center": "_Test Cost Center - _TC",
					"calculate_based_on": "Net Total",
					"conditions": [
						{
							"doctype": "Shipping Rule Condition",
							"from_value": 0,
							"to_value": 100000,
							"shipping_amount": 200,
						}
					],
					"account": "_Test Account Shipping Charges - _TC",
				}
			).insert()
		else:
			frappe.set_value("Shipping Rule", "_Test Shipping Rule", "account", "Shipping Charges - _TC")

		frappe.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)
		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, rate=4000)

		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			cost_center="Main - _TC",
			item="_Test Item Home Desktop 100",
			qty=4,
			rate=5000,
			warehouse="Stores - _TC",
			currency="INR",
			selling_price_list="Standard Selling",
			shipping_rule="_Test Shipping Rule 1",
			update_stock=1,
		)
		self.assertEqual(sales_invoice.docstatus, 1)
		self.assertEqual(sales_invoice.status, "Unpaid")

		debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
		shipping_account = frappe.db.get_value("Shipping Rule", "_Test Shipping Rule", "account")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": sales_invoice.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertAlmostEqual(gl_debits[debtor_account], 20200)
		self.assertAlmostEqual(gl_credits[sales_account], 20000)
		self.assertAlmostEqual(gl_credits[shipping_account], 200)
		self.assertTrue("Stock In Hand - _TC" in gl_credits)
		self.assertTrue("Cost of Goods Sold - _TC" in gl_debits)
		shipping_rule_amount = frappe.db.get_value(
			"Sales Taxes and Charges",
			{"parent": sales_invoice.name, "account_head": shipping_account},
			"tax_amount",
		)
		self.assertAlmostEqual(shipping_rule_amount, 200)
		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": sales_invoice.name, "warehouse": "Stores - _TC"},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in sle]), -4)

	def test_sales_invoice_with_SR_and_CRN_TC_S_038(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")

		# Create or get inventory account if not exists
		if not frappe.db.exists("Account", "Stock In Hand - _TC"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Stock In Hand",
					"parent_account": "Current Assets - _TC",
					"company": "_Test Company",
					"account_type": "Stock",
					"is_group": 0,
				}
			).insert()

		# Set default accounts for test company
		frappe.set_value(
			"Company",
			"_Test Company",
			{
				"default_receivable_account": "Debtors - _TC",
				"default_income_account": "Sales - _TC",
				"default_expense_account": "Cost of Goods Sold - _TC",
				"default_inventory_account": "Stock In Hand - _TC",
				"enable_perpetual_inventory": 1,
			},
		)

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, rate=1000)

		sales_order = make_sales_order(
			item_code="_Test Item Home Desktop 100", qty=5, price_list_rate=3000, warehouse="Stores - _TC"
		)

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.insert()
		delivery_note.submit()
		sle_dn = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": delivery_note.name, "warehouse": "Stores - _TC"},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in sle_dn]), -5)

		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.insert()
		sales_invoice.submit()
		debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
		gl_entries_si = frappe.get_all(
			"GL Entry", filters={"voucher_no": sales_invoice.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_si = {entry.account: entry.debit for entry in gl_entries_si}
		gl_credits_si = {entry.account: entry.credit for entry in gl_entries_si}
		self.assertAlmostEqual(gl_debits_si[debtor_account], 15000)
		self.assertAlmostEqual(gl_credits_si[sales_account], 15000)

		dn_return = create_delivery_note(
			is_return=1,
			return_against=delivery_note.name,
			item="_Test Item Home Desktop 100",
			qty=-5,
			warehouse="Stores - _TC",
			do_not_save=True,
		)
		for i in dn_return.items:
			i.against_sales_order = sales_order.name
			sales_order_item = frappe.get_all(
				"Sales Order Item",
				filters={"parent": sales_order.name, "item_code": i.item_code},
				fields=["name"],
			)
			if sales_order_item:
				i.so_detail = sales_order_item[0].name

		dn_return.save()
		dn_return.submit()
		gl_entries_dn = frappe.get_all(
			"GL Entry", filters={"voucher_no": dn_return.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_dn = {entry.account: entry.debit for entry in gl_entries_dn}
		gl_credits_dn = {entry.account: entry.credit for entry in gl_entries_dn}
		inventory_account = frappe.db.get_value("Company", "_Test Company", "default_inventory_account")
		expense_account = frappe.db.get_value("Company", "_Test Company", "default_expense_account")

		self.assertAlmostEqual(gl_credits_dn[expense_account], 5000)
		self.assertAlmostEqual(gl_debits_dn[inventory_account], 5000)

		sle_dn_return = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": dn_return.name, "warehouse": "Stores - _TC"},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in sle_dn_return]), 5)

		crn = create_sales_invoice(
			item="_Test Item Home Desktop 100",
			qty=-5,
			rate=3000,
			is_return=1,
			return_against=sales_invoice.name,
			do_not_save=True,
		)
		for i in crn.items:
			i.sales_order = sales_order.name
		crn.save()
		crn.submit()

		gl_entries_crn = frappe.get_all(
			"GL Entry", filters={"voucher_no": crn.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_crn = {entry.account: entry.debit for entry in gl_entries_crn}
		gl_credits_crn = {entry.account: entry.credit for entry in gl_entries_crn}
		self.assertAlmostEqual(gl_debits_crn[sales_account], 15000)
		self.assertAlmostEqual(gl_credits_crn[debtor_account], 15000)

		sales_order.reload()
		self.assertEqual(sales_order.status, "To Deliver")

	def test_sales_invoice_with_sr_crn_and_payment_TC_S_039(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		# Set up required accounts if they don't exist
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		required_accounts = [
			("Stock In Hand - _TC", "Current Assets - _TC", "Stock"),
			("Cost of Goods Sold - _TC", "Cost of Goods Sold - _TC", "Cost of Goods Sold"),
			("Sales - _TC", "Income - _TC", "Income Account"),
			("Debtors - _TC", "Current Assets - _TC", "Receivable"),
		]

		for account_name, parent_account, account_type in required_accounts:
			if not frappe.db.exists("Account", account_name):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": account_name.split(" - ")[0],
						"parent_account": parent_account,
						"company": "_Test Company",
						"account_type": account_type,
						"is_group": 0,
					}
				).insert()

		# Set default accounts for test company
		frappe.set_value(
			"Company",
			"_Test Company",
			{
				"default_receivable_account": "Debtors - _TC",
				"default_income_account": "Sales - _TC",
				"default_expense_account": "Cost of Goods Sold - _TC",
				"default_inventory_account": "Stock In Hand - _TC",
				"enable_perpetual_inventory": 1,
			},
		)

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, rate=2500)

		sales_invoice = create_sales_invoice(
			warehouse="Stores - _TC",
			item_code="_Test Item Home Desktop 100",
			qty=5,
			rate=3000,
			income_account="Sales - _TC",
			expense_account="Cost of Goods Sold - _TC",
			update_stock=1,
		)

		stock_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": sales_invoice.name, "warehouse": "Stores - _TC"},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in stock_entries]), -5)

		gl_entries_si = frappe.get_all(
			"GL Entry", filters={"voucher_no": sales_invoice.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_si = {entry.account: entry.debit for entry in gl_entries_si}
		gl_credits_si = {entry.account: entry.credit for entry in gl_entries_si}
		debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
		inventory_account = frappe.db.get_value("Company", "_Test Company", "default_inventory_account")
		expense_account = frappe.db.get_value("Company", "_Test Company", "default_expense_account")

		self.assertAlmostEqual(gl_debits_si[debtor_account], 15000)
		self.assertAlmostEqual(gl_credits_si[sales_account], 15000)

		delivery_note = make_delivery_note(sales_invoice.name)
		delivery_note.save()
		delivery_note.submit()

		dn_return = create_delivery_note(
			is_return=1,
			return_against=delivery_note.name,
			item="_Test Item Home Desktop 100",
			qty=-2,
			warehouse="Stores - _TC",
		)
		dn_return.submit()

		gl_entries_dn = frappe.get_all(
			"GL Entry", filters={"voucher_no": dn_return.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_dn = {entry.account: entry.debit for entry in gl_entries_dn}
		gl_credits_dn = {entry.account: entry.credit for entry in gl_entries_dn}
		self.assertAlmostEqual(gl_credits_dn[expense_account], 5000)
		self.assertAlmostEqual(gl_debits_dn[inventory_account], 5000)

		crn = create_sales_invoice(
			item="_Test Item Home Desktop 100",
			qty=-2,
			rate=3000,
			is_return=1,
			update_stock=1,
			warehouse="Stores - _TC",
			return_against=sales_invoice.name,
		)

		gl_entries_crn = frappe.get_all(
			"GL Entry", filters={"voucher_no": crn.name}, fields=["account", "debit", "credit"]
		)
		gl_debits_crn = {entry.account: entry.debit for entry in gl_entries_crn}
		gl_credits_crn = {entry.account: entry.credit for entry in gl_entries_crn}

		self.assertAlmostEqual(gl_debits_crn[sales_account], 6000)
		self.assertAlmostEqual(gl_credits_crn[debtor_account], 6000)

		stock_entries_crn = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": crn.name, "warehouse": "Stores - _TC"},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in stock_entries_crn]), 2)

	def test_deferred_revenue_invoice_line_item_TC_ACC_039(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")

		create_cost_center(
			cost_center_name="_Test Cost Center",
			company="_Test Company",
			parent_cost_center="_Test Company - _TC",
		)

		create_account(
			account_name="_Test Receivable",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Receivable",
		)
		create_account(
			account_name="_Test Cash",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Cash",
		)
		create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
			account_currency="INR",
		)

		create_customer(
			customer_name="_Test Customer",
			currency="INR",
			company="_Test Company",
			account="_Test Receivable - _TC",
		)

		frappe.set_value(
			"Company",
			"_Test Company",
			{
				"default_receivable_account": "Debtors - _TC",
				"default_expense_account": "Cost of Goods Sold - _TC",
				"default_inventory_account": "Stock In Hand - _TC",
				"enable_perpetual_inventory": 1,
			},
		)
		item = make_test_item(item_name="_Test Item")
		item.enable_deferred_revenue = 1
		item.no_of_months = 12
		item.save()
		if item.is_new():
			item.append(
				"item_defaults",
				{
					"default_warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company",
					"selling_cost_center": "_Test Cost Center - _TC",
				},
			)
			item.save()

		customer = frappe.get_doc("Customer", "_Test Customer")
		sales_invoice = create_sales_invoice(
			item=item.name,
			qty=1,
			customer=customer.name,
			update_stock=1,
			warehouse="_Test Warehouse - _TC",
			cost_center="_Test Cost Center - _TC",
			account="_Test Receivable - _TC",
			company="_Test Company",
			currency="INR",
			rate=50000,
			do_not_submit=True,
		)
		if sales_invoice.items:
			sales_invoice.items[0].enable_deferred_revenue = 1
			sales_invoice.items[0].deferred_revenue_account = "Deferred Revenue - _TC"
		sales_invoice.save()
		sales_invoice.submit()
		expected_gl_entries = [
			["Cost of Goods Sold - _TC", 100.0, 0.0, sales_invoice.posting_date],
			["Stock In Hand - _TC", 0.0, 100.0, sales_invoice.posting_date],
			["Debtors - _TC", sales_invoice.grand_total, 0.0, sales_invoice.posting_date],
			["Deferred Revenue - _TC", 0.0, sales_invoice.grand_total, sales_invoice.posting_date],
		]
		check_gl_entries(self, sales_invoice.name, expected_gl_entries, sales_invoice.posting_date)
		frappe.db.rollback()

	def test_deferred_revenue_invoice_multiple_item_TC_ACC_040(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.get_item_details import calculate_service_end_date
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_cost_center(
			cost_center_name="_Test Cost Center",
			company="_Test Company",
			parent_cost_center="_Test Company - _TC",
		)

		create_account(
			account_name="_Test Receivable",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Receivable",
		)
		create_account(
			account_name="_Test Cash",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Cash",
		)

		create_customer(
			customer_name="_Test Customer",
			currency="INR",
			company="_Test Company",
			account="_Test Receivable - _TC",
		)

		items_list = ["_Test Item 1", "_Test Item 2"]
		for item in items_list:
			item = make_test_item(item_name=item)
			item.enable_deferred_expense = 1
			item.no_of_months_exp = 12
			item.save()

		customer = frappe.get_doc("Customer", "_Test Customer")
		sales_invoice = create_sales_invoice(
			item=items_list[0],
			qty=1,
			customer=customer.name,
			warehouse="_Test Warehouse - _TC",
			cost_center="_Test Cost Center - _TC",
			account="_Test Receivable - _TC",
			company="_Test Company",
			currency="INR",
			rate=50000,
			do_not_submit=True,
		)
		if sales_invoice.items:
			sales_invoice.items[0].enable_deferred_revenue = 1
			sales_invoice.items[0].deferred_revenue_account = "Deferred Revenue - _TC"
			sales_invoice.save()

		sales_invoice.append(
			"items",
			{
				"item_code": items_list[1],
				"item_name": items_list[1],
				"qty": 1,
				"rate": 50000,
				"warehouse": "_Test Warehouse - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"enable_deferred_revenue": 1,
				"deferred_revenue_account": "Deferred Revenue - _TC",
				"no_of_months": 12,
				"service_start_date": sales_invoice.posting_date,
			},
		)
		end_date_obj = calculate_service_end_date(args=sales_invoice.items[1].as_dict())
		sales_invoice.items[1].service_end_date = end_date_obj.get("service_end_date")
		sales_invoice.save()
		sales_invoice.submit()

		expected_gl_entries = [
			["Debtors - _TC", sales_invoice.grand_total, 0.0, sales_invoice.posting_date],
			["Deferred Revenue - _TC", 0.0, sales_invoice.grand_total, sales_invoice.posting_date],
		]
		check_gl_entries(self, sales_invoice.name, expected_gl_entries, sales_invoice.posting_date)

	def test_pos_returns_with_party_account_currency(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		pos_profile = make_pos_profile()
		pos_profile.payments = []
		pos_profile.append("payments", {"default": 1, "mode_of_payment": "Cash"})
		pos_profile.save()
		pos = create_sales_invoice(
			customer="_Test Customer USD",
			currency="USD",
			conversion_rate=86.595000000,
			qty=2,
			do_not_save=True,
		)
		pos.is_pos = 1
		pos.pos_profile = pos_profile.name
		pos.debit_to = "_Test Receivable USD - _TC"
		pos.append("payments", {"mode_of_payment": "Cash", "amount": 20.35})
		pos.save().submit()
		pos_return = make_sales_return(pos.name)
		self.assertEqual(abs(pos_return.payments[0].amount), pos.payments[0].amount)

	def test_create_return_invoice_for_self_update(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		invoice = create_sales_invoice()

		payment_entry = get_payment_entry(dt=invoice.doctype, dn=invoice.name)
		payment_entry.reference_no = "test001"
		payment_entry.reference_date = getdate()

		payment_entry.save()
		payment_entry.submit()

		r_invoice = make_return_doc(invoice.doctype, invoice.name)

		r_invoice.update_outstanding_for_self = 0
		r_invoice.save()

		self.assertEqual(r_invoice.update_outstanding_for_self, 1)

		r_invoice.submit()

		self.assertNotEqual(r_invoice.outstanding_amount, 0)

		invoice.reload()

		self.assertEqual(invoice.outstanding_amount, 0)

	def test_prevents_fully_returned_invoice_with_zero_quantity(self):
		from erpnext.controllers.sales_and_purchase_return import StockOverReturnError, make_return_doc

		invoice = create_sales_invoice(qty=10)

		return_doc = make_return_doc(invoice.doctype, invoice.name)
		return_doc.items[0].qty = -10
		return_doc.save().submit()

		return_doc = make_return_doc(invoice.doctype, invoice.name)
		return_doc.items[0].qty = 0

		self.assertRaises(StockOverReturnError, return_doc.save)

	def test_repost_account_ledger_for_si_TC_ACC_118(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.repost_accounting_ledger.test_repost_accounting_ledger import (
			update_repost_settings,
		)
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		update_repost_settings()
		company = "_Test Company"
		item = make_test_item(item_name="_Test Item")
		si = create_sales_invoice(customer="_Test Customer", company=company, item=item.name, rate=1000)
		ral = frappe.get_doc(
			{
				"doctype": "Repost Accounting Ledger",
				"company": company,
				"vouchers": [{"voucher_type": "Sales Invoice", "voucher_no": si.name}],
			}
		).insert()
		ral.submit()
		si.items[0].income_account = "_Test Account Cost for Goods Sold - _TC"
		si.db_update()
		si.submit()
		expected_gl_entries = [
			["Debtors - _TC", si.grand_total, 0.0, si.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 0.0, si.grand_total, si.posting_date],
		]
		check_gl_entries(self, si.name, expected_gl_entries, si.posting_date)

	def test_promotion_scheme_for_selling_TC_ACC_115(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		item = make_test_item("_Test Item Promotion")

		frappe.get_doc(
			{
				"doctype": "Promotional Scheme",
				"__newname": "_Test Promotional Scheme",
				"company": "_Test Company",
				"selling": 1,
				"valid_from": nowdate(),
				"valid_upto": add_days(nowdate(), 20),
				"currency": "INR",
				"items": [{"item_code": item.name, "uom": "Nos"}],
				"price_discount_slabs": [
					{
						"min_qty": "10",
						"max_qty": "100",
						"min_amount": 0,
						"max_amount": 0,
						"rate_or_discount": "Discount Percentage",
						"discount_percentage": 2,
						"rule_description": "2%",
					},
					{
						"min_qty": "101",
						"max_qty": "1000",
						"min_amount": 0,
						"max_amount": 0,
						"rate_or_discount": "Discount Percentage",
						"discount_percentage": 5,
						"rule_description": "5%",
					},
				],
			}
		).insert()

		si = create_sales_invoice(
			customer="_Test Customer",
			item=item.name,
			rate=1000,
			qty="10",
			company="_Test Company",
		)

		self.assertEqual(2, si.items[0].discount_percentage)

	def test_over_billing_allowance_for_si_TC_ACC_120(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_invoice, make_sales_order

		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.db_set("over_billing_allowance", 10)
		account_setting.save()
		company = "_Test Company"
		item = make_test_item("_Test Item")
		so = make_sales_order(
			customer="_Test Customer", company=company, item_code=item.name, rate=1000, qty=1
		)
		try:
			si = make_sales_invoice(so.name)
			si.items[0].rate = 1200
			si.save()
			si.submit()
		except Exception as e:
			error_msg = str(e)
			self.assertEqual(
				error_msg,
				'This document is over limit by Amount 100.0 for item _Test Item. Are you making another Sales Invoice against the same Sales Order Item?To allow over billing, update "Over Billing Allowance" in Accounts Settings or the Item.',
			)

	def test_create_sales_invoice_for_interstate_branch_transfer_TC_ACC_123(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		internal_customer = frappe.get_value(
			"Customer", {"is_internal_customer": 1, "represents_company": "_Test Company"}
		)
		if not internal_customer:
			customer = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "_Test Internal Customer 4",
					"customer_type": "Company",
					"is_internal_customer": 1,
					"represents_company": "_Test Company",
					"companies": [
						{
							"company": "_Test Company",
						}
					],
				}
			).insert()

		elif internal_customer:
			customer = frappe.get_doc("Customer", internal_customer)
		else:
			customer = frappe.get_doc("Customer", "_Test Internal Customer 4")

		item = make_test_item("_Test Item")
		si = create_sales_invoice(
			company="_Test Company",
			customer=customer.name,
			item=item.name,
			qty=1,
			rate=10000,
			do_not_submit=True,
		)
		si.taxes_and_charges = "Output GST Out-state - _TC"
		si.save()
		si.submit()
		expected_gl_entries = [
			["Output Tax IGST - _TC", 0.0, si.total_taxes_and_charges, si.posting_date],
			["Unrealized Profit - _TC", si.total_taxes_and_charges, 0.0, si.posting_date],
		]
		check_gl_entries(self, si.name, expected_gl_entries, si.posting_date)

	def test_create_sales_invoice_for_common_party_TC_ACC_124(self):
		from erpnext.accounts.doctype.party_link.party_link import create_party_link
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_account,
			create_purchase_invoice,
			create_supplier,
			make_test_item,
		)
		from erpnext.buying.doctype.purchase_order.test_purchase_order import validate_fiscal_year

		validate_fiscal_year("_Test Company")
		create_account()
		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.enable_common_party_accounting = True
		account_setting.save()
		supplier = create_supplier(supplier_name="_Test Common Party", company="_Test Company")
		if supplier.accounts:
			supplier.accounts.clear()
			supplier.flags.ignore_mandatory = True
			supplier.save()

		create_customer(customer_name="_Test Common Party", company="_Test Company")
		if not frappe.get_value(
			"Party Link",
			{
				"primary_party": "_Test Common Party",
				"secondary_party": "_Test Common Party",
				"primary_role": "Supplier",
			},
		):
			create_party_link(
				primary_role="Supplier", primary_party=supplier.name, secondary_party=supplier.name
			)

		item = make_test_item("_Test Item")
		pi = create_purchase_invoice(
			supplier=supplier.name, item_code=item.name, company="_Test Company", qty=1, rate=10000
		)
		pi.save().submit()

		si = create_sales_invoice(
			customer="_Test Common Party",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=15000,
			debit_to="Debtors - _TC",
		)
		jv_parent = frappe.get_value(
			"Journal Entry Account", {"reference_type": "Sales Invoice", "reference_name": si.name}, "parent"
		)
		jv_doc = frappe.get_doc("Journal Entry", jv_parent)
		expected_gl_entries = [
			["Creditors - _TC", jv_doc.total_credit, 0.0, jv_doc.posting_date],
			["Debtors - _TC", 0.0, jv_doc.total_debit, jv_doc.posting_date],
		]
		check_gl_entries(self, jv_doc.name, expected_gl_entries, jv_doc.posting_date, "Journal Entry")

	def test_prevent_sale_below_purchase_rate_TC_ACC_125(self):
		import frappe

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
			create_supplier,
			make_test_item,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")

		if not frappe.db.get_single_value("Selling Settings", "validate_selling_price"):
			frappe.db.set_single_value("Selling Settings", "validate_selling_price", 1)

		if not frappe.db.get_value("Company", "_Test Company", "stock_received_but_not_billed"):
			frappe.db.set_value(
				"Company",
				"_Test Company",
				"stock_received_but_not_billed",
				"Stock Received But Not Billed - _TC",
			)
		supplier = create_supplier(supplier_name="_Test Supplier")
		item = make_test_item("_Test Sell Item")

		# Purchase at 100
		pi = create_purchase_invoice(
			supplier=supplier.name, company="_Test Company", item_code=item.name, qty=1, rate=100
		)
		pi.save().submit()

		expected_msg = (
			"Row #1: Selling rate for item _Test Item is lower than its last purchase rate.\n"
			"\t\t\t\t\tSelling net rate should be atleast 100.0.Alternatively,\n"
			"\t\t\t\t\tyou can disable selling price validation in Selling Settings to bypass\n"
			"\t\t\t\t\tthis validation."
		)
		si = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=99,
			do_not_save=1,
		)
		with self.assertRaises(frappe.ValidationError) as context:
			si.save()
		self.assertEqual(str(context.exception), expected_msg)

		frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)

	def test_test_unlink_payment_on_invoice_cancellation_TC_ACC_126(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		si_name = None
		pe_name = None
		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.unlink_payment_on_cancellation_of_invoice = 0
		account_setting.save()
		item = make_test_item("_Test Item")
		try:
			si = create_sales_invoice(
				customer="_Test Customer", company="_Test Company", item_code=item.name, qty=1, rate=100
			)
			si_name = si.name
			pe = get_payment_entry(si.doctype, si.name, bank_account="Cash - _TC")
			pe.submit()
			pe_name = pe.name
			si.load_from_db()

			si.cancel()
		except Exception as e:
			error_msg = str(e)
			self.assertEqual(
				error_msg,
				f"Cannot delete or cancel because Sales Invoice {si_name} is linked with Payment Entry {pe_name} at Row: 1",
			)

	def test_si_cancel_amend_with_item_details_change_TC_S_128(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		make_test_item("_Test Item 1")
		make_stock_entry(item_code="_Test Item", qty=5, rate=1000, target="_Test Warehouse - _TC")
		make_stock_entry(item_code="_Test Item 1", qty=5, rate=1000, target="_Test Warehouse - _TC")
		si = create_sales_invoice(qty=2, rate=500)
		si.cancel()
		si.reload()
		self.assertEqual(si.status, "Cancelled")

		amended_si = frappe.copy_doc(si)
		amended_si.docstatus = 0
		amended_si.amended_from = si.name
		amended_si.items[0].item_code = "_Test Item 1"
		amended_si.save()
		amended_si.submit()
		self.assertEqual(amended_si.status, "Unpaid")

	def test_si_cancel_amend_with_customer_change_TC_S_129(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_customer(customer_name="_Test Customer Selling", company="_Test Company")
		make_stock_entry(item_code="_Test Item", qty=5, rate=1000, target="_Test Warehouse - _TC")

		si = create_sales_invoice(qty=2, rate=500)
		si.cancel()
		si.reload()
		self.assertEqual(si.status, "Cancelled")

		amended_si = frappe.copy_doc(si)
		amended_si.docstatus = 0
		amended_si.amended_from = si.name
		amended_si.customer = "_Test Customer Selling"
		amended_si.customer_address = ""
		amended_si.shipping_address_name = ""
		amended_si.save()
		amended_si.submit()
		self.assertEqual(amended_si.status, "Unpaid")

	def test_si_cancel_amend_with_payment_terms_change_TC_S_130(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_term,
			create_payment_terms_template,
		)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=5, rate=1000, target="_Test Warehouse - _TC")
		create_payment_term("Basic Amount Receivable for Selling")

		if not frappe.db.exists("Payment Terms Template", "Test Receivable Template Selling"):
			frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": "Test Receivable Template Selling",
					"allocate_payment_based_on_payment_terms": 1,
					"terms": [
						{
							"doctype": "Payment Terms Template Detail",
							"payment_term": "Basic Amount Receivable for Selling",
							"invoice_portion": 100,
							"credit_days_based_on": "Day(s) after invoice date",
							"credit_days": 1,
						}
					],
				}
			).insert()

		create_payment_terms_template()
		si = create_sales_invoice(qty=2, rate=500, do_not_save=True)
		si.payment_terms_template = "Test Receivable Template"
		si.save()
		si.submit()
		si.cancel()
		si.reload()
		self.assertEqual(si.status, "Cancelled")
		amended_si = frappe.copy_doc(si)
		amended_si.docstatus = 0
		amended_si.due_date = si.due_date
		amended_si.amended_from = si.name
		amended_si.payment_terms_template = "Test Receivable Template Selling"
		for idx, payment_schedule in enumerate(amended_si.payment_schedule):
			payment_schedule.due_date = add_days(amended_si.posting_date, idx)
		amended_si.save()
		amended_si.submit()

		self.assertEqual(amended_si.status, "Unpaid")

	def test_si_credit_note_cancel_amend_with_payment_terms_change_TC_S_131(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_term,
			create_payment_terms_template,
		)
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		make_stock_entry(item_code="_Test Item", qty=5, rate=1000, target="_Test Warehouse - _TC")
		create_payment_term("Basic Amount Receivable for Selling")

		if not frappe.db.exists("Payment Terms Template", "Test Receivable Template Selling"):
			frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": "Test Receivable Template Selling",
					"allocate_payment_based_on_payment_terms": 1,
					"terms": [
						{
							"doctype": "Payment Terms Template Detail",
							"payment_term": "Basic Amount Receivable for Selling",
							"invoice_portion": 100,
							"credit_days_based_on": "Day(s) after invoice date",
							"credit_days": 1,
						}
					],
				}
			).insert()

		create_payment_terms_template()
		si = create_sales_invoice(qty=2, rate=500, do_not_save=True)
		si.payment_terms_template = "Test Receivable Template"
		si.save()
		si.submit()
		self.assertEqual(si.status, "Unpaid")

		sir = make_sales_return(si.name)
		sir.save()
		sir.submit()
		sir.cancel()
		self.assertEqual(sir.status, "Cancelled")

		amended_sir = frappe.copy_doc(sir)
		amended_sir.docstatus = 0
		amended_sir.amended_from = sir.name
		amended_sir.payment_terms_template = "Test Receivable Template Selling"
		amended_sir.save()
		amended_sir.submit()

		self.assertEqual(amended_sir.status, "Return")

	def test_si_with_deferred_revenue_item_TC_S_135(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		item = make_test_item("_Test Item 1")
		item.enable_deferred_revenue = 1
		item.no_of_months = 5
		item.save()

		make_stock_entry(item_code="_Test Item 1", qty=10, rate=5000, target="_Test Warehouse - _TC")

		deferred_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)
		si = create_sales_invoice(item=item.name, qty=5, rate=3000, do_not_submit=True)
		si.items[0].enable_deferred_revenue = 1
		si.items[0].deferred_revenue_account = deferred_account
		si.save()
		si.submit()
		self.assertEqual(si.status, "Unpaid")

	def test_si_with_sr_calculate_with_fixed_TC_S_139(self):
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		create_fiscal_year("_Test Company")
		create_item("_Test Item 1")
		create_customer(customer_name="_Test Customer", company="_Test Company")
		shipping_rule = create_shipping_rule(
			shipping_rule_type="Selling",
			shipping_rule_name="Shipping Rule - Test Fixed",
			args={"calculate_based_on": "Fixed", "shipping_amount": 100},
		)
		self.assertEqual(shipping_rule.docstatus, 1)
		make_stock_entry(item_code="_Test Item 1", qty=10, rate=500, target="_Test Warehouse - _TC")
		si = create_sales_invoice(
			do_not_submit=True,
			do_not_save=True,
			item_list=[
				{
					"item_code": "_Test Item 1",
					"qty": 5,
					"rate": 200,
					"warehouse": "_Test Warehouse - _TC",
					"income_account": "Sales - _TC",
					"cost_center": "_Test Cost Center - _TC",
					"deferred_revenue_account": "Deferred Revenue - _TC",
				}
			],
		)
		si.calculate_taxes_and_totals()
		si.shipping_rule = shipping_rule.name
		si.insert()
		si.submit()

		self.assertEqual(si.net_total, 1000)
		self.assertEqual(si.total_taxes_and_charges, 100)
		self.assertEqual(si.grand_total, 1100)
		frappe.db.rollback()

	def test_si_with_sr_calculate_with_net_total_TC_S_140(self):
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		item = create_item("_Test Item 1")
		shipping_rule = create_shipping_rule(
			shipping_rule_type="Selling",
			shipping_rule_name="Shipping Rule - Test Net Total",
			args={"calculate_based_on": "Net Total"},
		)
		self.assertEqual(shipping_rule.docstatus, 1)
		make_stock_entry(item_code=item.name, qty=10, rate=500, target="_Test Warehouse - _TC")
		si = create_sales_invoice(item_code=item.name, qty=5, rate=200, do_not_submit=True)

		si.shipping_rule = shipping_rule.name
		si.save()
		si.submit()

		self.assertEqual(si.net_total, 1000)

		self.assertEqual(si.total_taxes_and_charges, 200)
		self.assertEqual(si.grand_total, 1200)

	def test_si_with_sr_calculate_with_net_weight_TC_S_141(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		shipping_rule = create_shipping_rule(
			shipping_rule_type="Selling",
			shipping_rule_name="Shipping Rule - Test Net Weight",
			args={"calculate_based_on": "Net Weight"},
		)
		self.assertEqual(shipping_rule.docstatus, 1)

		item = make_test_item("_Test Item 1")
		item.weight_per_unit = 250
		item.weight_uom = "Nos"
		item.save
		make_stock_entry(item_code="_Test Item 1", qty=10, rate=500, target="_Test Warehouse - _TC")
		si = create_sales_invoice(item=item.name, qty=5, rate=200, do_not_submit=True)

		si.shipping_rule = shipping_rule.name
		si.items[0].weight_per_unit = 250
		si.items[0].weight_uom = "Nos"
		si.save()
		si.submit()

		self.assertEqual(si.net_total, 1000)
		self.assertEqual(si.total_taxes_and_charges, 200)
		self.assertEqual(si.grand_total, 1200)

	def test_fetch_payment_terms_from_order_TC_ACC_129(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_invoice, make_sales_order

		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.automatically_fetch_payment_terms = 1
		account_setting.save()

		item = make_test_item("_Test Item")

		so = make_sales_order(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
		)
		so.payment_terms_template = "_Test Payment Term Template"
		so.save().submit()

		si = make_sales_invoice(so.name)
		self.assertEqual(si.payment_terms_template, "_Test Payment Term Template")

	@if_app_installed("india_compliance")
	def test_generate_sales_invoice_with_items_different_gst_rates_TC_ACC_131(self):
		import json

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		item = make_test_item("_Test GST Item")

		gst_rates = [
			{"rate": 5, "template": "GST 5% - _TC", "range": (500, 1000)},
			{"rate": 12, "template": "GST 12% - _TC", "range": (1001, 10000)},
			{"rate": 18, "template": "GST 18% - _TC", "range": (10001, 100000)},
		]

		if not item.taxes:
			for gst in gst_rates:
				item.append(
					"taxes",
					{
						"item_tax_template": gst["template"],
						"valid_from": frappe.utils.add_months(nowdate(), -1),
						"minimum_net_rate": gst["range"][0],
						"maximum_net_rate": gst["range"][1],
					},
				)
				item.save()
		rate_tax = [
			{"total_amount": 25, "total_tax": 5, "item_rate": 500},
			{"total_amount": 132, "total_tax": 12, "item_rate": 1100},
			{"total_amount": 1980, "total_tax": 18, "item_rate": 11000},
		]
		for rate in rate_tax:
			si = create_sales_invoice(
				customer="_Test Customer",
				company="_Test Company",
				item_code=item.name,
				qty=1,
				rate=rate.get("item_rate"),
				do_not_submit=True,
			)
			si.taxes_and_charges = "Output GST In-state - _TC"
			si.save()
			total_tax = 0.0
			total_amount = 0.0
			for taxes in si.taxes:
				item_wise_tax_detail = taxes.item_wise_tax_detail

				if isinstance(item_wise_tax_detail, str):
					item_wise_tax_detail = json.loads(item_wise_tax_detail)

				if "_Test GST Item" in item_wise_tax_detail:
					total_tax += item_wise_tax_detail["_Test GST Item"][0]
					total_amount += item_wise_tax_detail["_Test GST Item"][1]
			self.assertEqual(total_tax, rate.get("total_tax"))
			self.assertEqual(total_amount, rate.get("total_amount"))

	def test_determine_address_tax_category_from_billing_address_TC_ACC_134(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.party import get_address_tax_category

		address_args = [
			{
				"name": "_Test Company Address-Office",
				"address_title": "_Test Company Address",
				"address_type": "Office",
				"is_primary_address": 1,
				"state": "Maharashtra",
				"pincode": "423701",
				"address_line1": "Test Address 10",
				"country": "India",
				"is_your_company_address": 1,
				"company": "_Test Company",
			},
			{
				"name": "Customer Billing Address-Billing",
				"address_title": "Customer Billing Address",
				"address_type": "Billing",
				"is_primary_address": 0,
				"address_line1": "Test Address 11",
				"state": "Karnataka",
				"pincode": "587316",
				"country": "India",
				"is_your_company_address": 0,
				"doctype": "Customer",
				"docname": "_Test Customer",
			},
			{
				"name": "Customer Shipping Address-Shipping",
				"address_title": "Customer Shipping Address",
				"address_type": "Shipping",
				"is_primary_address": 0,
				"address_line1": "Test Address 11",
				"state": "Kerala",
				"pincode": "686582",
				"country": "India",
				"is_your_company_address": 0,
				"doctype": "Customer",
				"docname": "_Test Customer",
			},
		]
		for d in address_args:
			create_address(**d)

		company_address = frappe.get_doc("Address", "_Test Company Address-Office")
		customer_billing = frappe.get_doc("Address", "Customer Billing Address-Billing")
		if (
			company_address.state
			and customer_billing.state
			and company_address.state == customer_billing.state
		):
			customer_billing.tax_category = "In-State"
		else:
			customer_billing.tax_category = "Out-State"
		customer_billing.save()

		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.determine_address_tax_category_from = "Billing Address"
		account_setting.save()

		self.assertEqual("Billing Address", account_setting.determine_address_tax_category_from)

		item = make_test_item("_Test Item")
		tax_category = get_address_tax_category(None, customer_billing.name, None)
		si = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
		)
		si.customer_address = customer_billing.name
		si.company_address = company_address.name
		si.tax_category = tax_category
		si.save()
		self.assertEqual(tax_category, si.tax_category)

	def test_determine_address_tax_category_from_shipping_address_TC_ACC_135(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.party import get_address_tax_category

		address_args = [
			{
				"name": "_Test Company Address-Office",
				"address_title": "_Test Company Address",
				"address_type": "Office",
				"is_primary_address": 1,
				"state": "Maharashtra",
				"pincode": "423701",
				"address_line1": "Test Address 10",
				"country": "India",
				"is_your_company_address": 1,
				"company": "_Test Company",
			},
			{
				"name": "Customer Billing Address-Billing",
				"address_title": "Customer Billing Address",
				"address_type": "Billing",
				"is_primary_address": 0,
				"address_line1": "Test Address 11",
				"state": "Karnataka",
				"pincode": "587316",
				"country": "India",
				"is_your_company_address": 0,
				"doctype": "Customer",
				"docname": "_Test Customer",
			},
			{
				"name": "Customer Shipping Address-Shipping",
				"address_title": "Customer Shipping Address",
				"address_type": "Shipping",
				"is_primary_address": 0,
				"address_line1": "Test Address 11",
				"state": "Kerala",
				"pincode": "686582",
				"country": "India",
				"is_your_company_address": 0,
				"doctype": "Customer",
				"docname": "_Test Customer",
			},
		]
		for d in address_args:
			create_address(**d)

		company_address = frappe.get_doc("Address", "_Test Company Address-Office")
		customer_shipping = frappe.get_doc("Address", "Customer Billing Address-Billing")
		if (
			company_address.state
			and customer_shipping.state
			and company_address.state == customer_shipping.state
		):
			customer_shipping.tax_category = "In-State"
		else:
			customer_shipping.tax_category = "Out-State"
		customer_shipping.save()

		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.determine_address_tax_category_from = "Billing Address"
		account_setting.save()

		self.assertEqual("Billing Address", account_setting.determine_address_tax_category_from)

		item = make_test_item("_Test Item")
		tax_category = get_address_tax_category(None, customer_shipping.name, None)
		si = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
		)
		si.customer_address = customer_shipping.name
		si.company_address = company_address.name
		si.tax_category = tax_category
		si.save()
		self.assertEqual(tax_category, si.tax_category)

	def test_si_to_pi_for_service_internal_transfer_TC_B_126(self):
		frappe.set_user("Administrator")
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		get_required_data = create_company_and_supplier()
		parent_company = get_required_data.get("parent_company")
		child_company = get_required_data.get("child_company")
		supplier = get_required_data.get("supplier")
		customer = get_required_data.get("customer")
		price_list = get_required_data.get("price_list")
		item_name = make_test_item("test_service")

		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": parent_company,
				"customer": customer,
				"due_date": today(),
				"currency": "INR",
				"selling_price_list": price_list,
				"taxes_and_charges": "Output GST In-state - TC-1",
				"items": [
					{
						"item_code": item_name,
						"qty": 1,
						"rate": 1000,
					}
				],
			}
		)
		si.insert()
		si.submit()
		self.assertEqual(si.company, parent_company)
		self.assertEqual(si.customer, customer)
		self.assertEqual(si.selling_price_list, price_list)
		self.assertEqual(si.items[0].rate, 1000)
		self.assertEqual(si.total, 1000)
		self.assertEqual(si.total_taxes_and_charges, 180)
		self.assertEqual(si.grand_total, 1180)

		gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Debtors - TC-1": {"debit": 1180, "credit": 0},
			"Output Tax CGST - TC-1": {"debit": 0, "credit": 90},
			"Output Tax SGST - TC-1": {"debit": 0, "credit": 90},
			"Sales - TC-1": {"debit": 0, "credit": 1000},
		}
		for entry in gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_inter_company_purchase_invoice(si.name)
		pi.bill_no = "test bill"
		pi.taxes_and_charges = "Input GST In-state - TC-3"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.company, child_company)
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.items[0].rate, 1000)
		self.assertEqual(pi.total, 1000)
		self.assertEqual(pi.total_taxes_and_charges, 180)
		self.assertEqual(pi.grand_total, 1180)

		gle_entries_pi = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-3": {"debit": 1000, "credit": 0},
			"Input Tax CGST - TC-3": {"debit": 90, "credit": 0},
			"Input Tax SGST - TC-3": {"debit": 90, "credit": 0},
			"Creditors - TC-3": {"debit": 0, "credit": 1180},
		}
		for entry in gle_entries_pi:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	def test_direct_sales_invoice_via_update_stock_TC_SCK_132(self):
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		customer = "_Test Customer"
		warehouse = "_Test Warehouse - _TC"
		item_code = "_Test Item 4"
		qty = 5
		item = create_item(item_code, is_stock_item=1, company="_Test Company", warehouse=warehouse)
		# Create stock entry to add initial stock
		make_stock_entry(item_code=item.name, qty=10, rate=100, target=warehouse)

		# Create Sales Invoice
		si = create_sales_invoice(
			customer=customer,
			warehouse=warehouse,
			item_code=item.name,
			qty=qty,
			rate=100,
			update_stock=1,
			do_not_submit=True,
		)
		si.save()
		si.submit()

		# Check Stock Ledger Entry
		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": si.name, "warehouse": warehouse},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in sle]), -qty)

		# Check GL Entry
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		print("gl_entry", gl_entries)
		expected_gl_entries = {
			"Debtors - _TC": 500,
			"Sales - _TC": -500,
			"Stock Asset - _TC": -500,
			"Cost of Goods Sold - _TC": 500,
		}
		for entry in gl_entries:
			self.assertEqual(expected_gl_entries.get(entry.account, 0), entry.debit - entry.credit)

	def test_sales_invoice_with_child_item_rates_of_product_bundle_TC_S_152(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		selling_setting = frappe.get_doc("Stock Settings")
		selling_setting.editable_bundle_item_rates = 1
		selling_setting.save()

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

		si.transaction_date = nowdate()
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(si.grand_total, 100)

	def test_sales_invoice_creating_dunning_from_si_TC_S_154(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		item = make_test_item("_Test Item")
		si = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=False,
		)

		self.assertEqual(si.status, "Unpaid")

		if not frappe.db.exists("Dunning Type", "_Test Dunning"):
			dun_type = frappe.new_doc("Dunning Type")
			dun_type.dunning_type = "_Test Dunning"
			dun_type.company = "_Test Company"
			dun_type.rate_of_interest = 5.0
			dun_type.save()

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import create_dunning

		dun = create_dunning(si.name)
		dun.posting_date = add_days(nowdate(), 1)
		dun.dunning_type = "_Test Dunning"
		dun.rate_of_interest = 5.0
		dun.save()
		dun.submit()
		dun.reload()

		self.assertEqual(dun.grand_total, 1000.136986301)

	def test_internal_goods_supply_TC_B_127(self):
		frappe.set_user("Administrator")
		# SO =>PO, SO => DN => PR, From DN => SI => PI (For goods)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_delivery_note,
			make_inter_company_purchase_order,
		)
		from erpnext.stock.doctype.delivery_note.delivery_note import (
			make_inter_company_purchase_receipt,
			make_sales_invoice,
		)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_required_data = create_company_and_supplier()

		parent_company = get_required_data.get("parent_company")
		get_required_data.get("child_company")
		get_required_data.get("supplier")
		customer = get_required_data.get("customer")
		price_list = get_required_data.get("price_list")
		item = make_test_item("test_service")
		get_or_create_fiscal_year("Test Company-3344")
		get_or_create_fiscal_year("Test Company-1122")
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"company": parent_company,
				"customer": customer,
				"currency": "INR",
				"transaction_date": today(),
				"set_warehouse": "Stores - TC-1",
				"selling_price_list": price_list,
				"taxes_and_charges": "Output GST In-state - TC-1",
				"items": [{"item_code": item.item_code, "qty": 1, "rate": 1000, "delivery_date": today()}],
			}
		)
		so.insert()
		so.submit()
		self.assertEqual(so.docstatus, 1)
		self.assertEqual(so.total, 1000)
		self.assertEqual(so.total_taxes_and_charges, 180)
		self.assertEqual(so.grand_total, 1180)

		po = make_inter_company_purchase_order(so.name)
		po.schedule_date = today()
		po.set_warehouse = "Stores - TC-3"
		po.taxes_and_charges = "Input GST In-state - TC-3"

		po.insert()
		po.submit()

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(po.total, 1000)
		self.assertEqual(po.total_taxes_and_charges, 180)
		self.assertEqual(po.grand_total, 1180)

		make_stock_entry(
			company=parent_company, target="Stores - TC-1", item_code=item.item_code, qty=10, rate=1000
		)

		dn = make_delivery_note(so.name)
		dn.insert()
		dn.submit()

		self.assertEqual(dn.docstatus, 1)
		self.assertEqual(dn.total, 1000)
		self.assertEqual(dn.total_taxes_and_charges, 180)
		self.assertEqual(dn.grand_total, 1180)

		get_dn_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_dn_stock_ledger[0].get("warehouse"), "Stores - TC-1")
		self.assertEqual(get_dn_stock_ledger[0].get("actual_qty"), -1)

		dn_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": dn.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Cost of Goods Sold - TC-1": {"debit": 1000, "credit": 0},
			"Stock In Hand - TC-1": {"debit": 0, "credit": 1000},
		}
		for entry in dn_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pr = make_inter_company_purchase_receipt(dn.name)
		pr.taxes_and_charges = "Input GST In-state - TC-3"
		pr.insert()
		pr.submit()

		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.total, 1000)
		self.assertEqual(pr.total_taxes_and_charges, 180)
		self.assertEqual(pr.grand_total, 1180)

		get_pr_stock_ledger = frappe.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["warehouse", "actual_qty"],
		)
		self.assertEqual(get_pr_stock_ledger[0].get("warehouse"), "Stores - TC-3")
		self.assertEqual(get_pr_stock_ledger[0].get("actual_qty"), 1)

		pr_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pr.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Stock In Hand - TC-3": {"debit": 1000, "credit": 0},
			"Stock Received But Not Billed - TC-3": {"debit": 0, "credit": 1000},
		}
		for entry in pr_gle_entries:
			for key in expected_si_entries:
				if entry["account"] == key:
					self.assertEqual(entry["debit"], expected_si_entries[key].get("debit", 0))
					self.assertEqual(entry["credit"], expected_si_entries[key].get("credit", 0))

		si = make_sales_invoice(dn.name)
		si.insert()
		si.submit()

		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.total, 1000)
		self.assertEqual(si.total_taxes_and_charges, 180)
		self.assertEqual(si.grand_total, 1180)

		si_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		expected_si_entries = {
			"Debtors - TC-1": {"debit": 1180, "credit": 0},
			"Output Tax CGST - TC-1": {"debit": 0, "credit": 90},
			"Output Tax SGST - TC-1": {"debit": 0, "credit": 90},
			"Sales - TC-1": {"debit": 0, "credit": 1000},
		}
		for entry in si_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

		pi = make_inter_company_purchase_invoice(si.name)
		pi.bill_no = "test bill"
		pi.taxes_and_charges = "Input GST In-state - TC-3"
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.total, 1000)
		self.assertEqual(pi.total_taxes_and_charges, 180)
		self.assertEqual(pi.grand_total, 1180)

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		expected_pi_entries = {
			"Stock Received But Not Billed - TC-3": {"debit": 1000, "credit": 0},
			"Input Tax CGST - TC-3": {"debit": 90, "credit": 0},
			"Input Tax SGST - TC-3": {"debit": 90, "credit": 0},
			"Creditors - TC-3": {"debit": 0, "credit": 1180},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

	def test_sales_invoice_ignoring_pricing_rule_TC_S_156(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_item("_Test Item")
		create_uom("_Test UOM")
		create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")
		create_customer(customer_name="_Test Customer", company="_Test Company")

		if not frappe.db.exists("Pricing Rule", {"title": "Test Offer"}):
			pricing_rule_doc = frappe.new_doc("Pricing Rule")
			pricing_rule_data = {
				"title": "Test Offer",
				"apply_on": "Item Code",
				"price_or_product_discount": "Price",
				"selling": 1,
				"min_qty": 10,
				"company": "_Test Company",
				"margin_type": "Percentage",
				"discount_percentage": 10,
				"for_price_list": "Standard Selling",
				"items": [{"item_code": "_Test Item", "uom": "_Test UOM"}],
			}

			pricing_rule_doc.update(pricing_rule_data)
			pricing_rule_doc.save()

		if not frappe.db.exists("Item Price", {"item_code": "_Test Item"}):
			ip_doc = frappe.new_doc("Item Price")
			item_price_data = {
				"item_code": "_Test Item",
				"uom": "_Test UOM",
				"price_list": "Standard Selling",
				"selling": 1,
				"price_list_rate": 1000,
			}
			ip_doc.update(item_price_data)
			ip_doc.save()

		si = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code="_Test Item",
			qty=1,
			rate=1000,
			do_not_save=True,
		)

		si.ignore_pricing_rule = 1
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(si.grand_total, 1000)

	@change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_sales_invoice_to_allow_item_multiple_times_TC_S_159(self):
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		si_items = [
			{"item_code": "_Test Item", "qty": 1, "rate": 200},
			{"item_code": "_Test Item", "qty": 1, "rate": 200},
		]

		si = create_sales_invoice(
			customer="_Test Customer", company="_Test Company", item_list=si_items, do_not_submit=False
		)
		self.assertEqual(si.status, "Unpaid")

	@change_settings("Selling Settings", {"dont_reserve_sales_order_qty_on_sales_return": 1})
	def test_sales_invoice_dont_reserve_sales_order_qty_on_sales_return_TC_S_158(self):
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		si = create_sales_invoice(
			qty=1, rate=300, update_stock=1, warehouse="_Test Warehouse - _TC", do_not_submit=0
		)
		self.assertEqual(si.status, "Unpaid")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, -1)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		si_return = make_sales_return(si.name)
		si_return.save().submit()
		si_return.reload()

		self.assertEqual(si_return.status, "Return")

		qty_change = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "_Test Item", "voucher_no": si_return.name, "warehouse": "_Test Warehouse - _TC"},
			"actual_qty",
		)
		self.assertEqual(qty_change, 1)

	def test_calculate_commission_for_sales_partner_TC_ACC_143(self):
		from frappe.tests.utils import if_app_installed

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.utils import get_fiscal_year
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		fiscal_year = get_fiscal_year(nowdate())[0]
		if if_app_installed("Sales Commission"):
			if not frappe.db.exists("Monthly Distribution", "_Test Sales Distribution"):
				month_distribution = frappe.get_doc(
					{
						"distribution_id": "_Test Sales Distribution",
						"doctype": "Monthly Distribution",
						"fiscal_year": fiscal_year,
					}
				)
				get_months(month_distribution)
				month_distribution.insert()
			if not frappe.db.exists("Sales Partner", "_Test Sales Distributor"):
				month_distribution = frappe.get_doc("Monthly Distribution", "_Test Sales Distribution")

				frappe.get_doc(
					{
						"partner_name": "_Test Sales Distributor",
						"doctype": "Sales Partner",
						"territory": "All Territories",
						"sales_person": "_Test Sales Commission",
						"partner_type": "Distributor",
						"commission_rate": 5,
						"targets": [
							{
								"item_group": "_Test Item Group",
								"fiscal_year": fiscal_year,
								"target_qty": 10,
								"target_amount": 1000,
								"distribution_id": month_distribution.name,
							}
						],
					}
				).insert()
			customer = frappe.get_doc("Customer", "_Test Customer")
			customer.default_sales_partner = "_Test Sales Distributor"
			customer.default_commission_rate = 5
			customer.save()
			item = make_test_item("_Test Item 3")
			si = create_sales_invoice(
				customer="_Test Customer",
				company="_Test Company",
				item_code=item.name,
				qty=10,
				rate=1000,
				do_not_submit=True,
			)
			si.submit()
			self.assertEqual(si.total_commission, 500)
			self.assertEqual(si.commission_rate, 5)
			self.assertEqual(si.amount_eligible_for_commission, 10000)
			self.assertEqual(si.sales_partner, "_Test Sales Distributor")

	def test_payment_term_discount_for_si_at_fully_paid_TC_ACC_097(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		if not frappe.db.exists("Payment Term", "_Test Discount Term"):
			frappe.get_doc(
				{
					"doctype": "Payment Term",
					"payment_term_name": "_Test Discount Term",
					"invoice_portion": 100,
					"mode_of_payment": "Cash",
					"discount_type": "Percentage",
					"due_date_based_on": "Day(s) after invoice date",
					"discount": 10,
				}
			).insert()

		frappe.get_doc("Payment Term", "_Test Discount Term")

		item = make_test_item("_Test Item")
		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
			do_not_save=True,
		)
		sales_invoice.append(
			"payment_schedule",
			{
				"payment_term": "_Test Discount Term",
				"due_date": add_days(nowdate(), 1),
				"invoice_portion": 100,
				"payment_amount": sales_invoice.grand_total,
				"discount_date": add_days(nowdate(), 1),
			},
		)
		sales_invoice.insert().submit()
		pe = get_payment_entry(
			sales_invoice.doctype, sales_invoice.name, bank_account="Cash - _TC", reference_date=nowdate()
		)
		pe.reference_no = "1"
		pe.deductions[0].account = "_Test Account Discount - _TC"
		pe.save().submit()
		expected_gle = [
			["Cash - _TC", (sales_invoice.grand_total - sales_invoice.grand_total * 0.1), 0.0, nowdate()],
			["Debtors - _TC", 0.0, sales_invoice.grand_total, nowdate()],
			["_Test Account Discount - _TC", sales_invoice.grand_total * 0.1, 0.0, nowdate()],
		]
		check_gl_entries(
			self,
			voucher_no=pe.name,
			expected_gle=expected_gle,
			posting_date=nowdate(),
			voucher_type="Payment Entry",
		)

	def test_payment_term_discount_for_si_at_partially_paid_TC_ACC_099(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		if not frappe.db.exists("Payment Term", "_Test partially Discount Term"):
			frappe.get_doc(
				{
					"doctype": "Payment Term",
					"payment_term_name": "_Test partially Discount Term",
					"invoice_portion": 70,
					"mode_of_payment": "Cash",
					"discount_type": "Percentage",
					"due_date_based_on": "Day(s) after invoice date",
					"discount": 5.0,
				}
			).insert()

		frappe.get_doc("Payment Term", "_Test partially Discount Term")

		item = make_test_item("_Test Item")
		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
			do_not_save=True,
		)

		sales_invoice.append(
			"payment_schedule",
			{
				"payment_term": "_Test partially Discount Term",
				"due_date": add_days(nowdate(), 1),
				"invoice_portion": 70,
				"payment_amount": 1000 * 0.7,
				"discount_date": add_days(nowdate(), 1),
			},
		)
		sales_invoice.insert().submit()
		pe = get_payment_entry(
			sales_invoice.doctype, sales_invoice.name, bank_account="Cash - _TC", reference_date=nowdate()
		)
		pe.reference_no = "1"
		pe.deductions[0].account = "_Test Account Discount - _TC"
		pe.save().submit()
		expected_gle = [
			["Cash - _TC", (sales_invoice.grand_total - sales_invoice.grand_total * 0.05), 0.0, nowdate()],
			["Debtors - _TC", 0.0, sales_invoice.grand_total, nowdate()],
			["_Test Account Discount - _TC", sales_invoice.grand_total * 0.05, 0.0, nowdate()],
		]
		check_gl_entries(
			self,
			voucher_no=pe.name,
			expected_gle=expected_gle,
			posting_date=nowdate(),
			voucher_type="Payment Entry",
		)

	def test_tax_with_holding_with_si_TC_ACC_109(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_account as create_account_all,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule
		from erpnext.accounts.doctype.tax_withholding_category.test_tax_withholding_category import (
			create_tax_withholding_category,
		)
		from erpnext.accounts.utils import get_fiscal_year
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		create_account_all()
		create_customer(customer_name="_Test Customer", company="_Test Company")
		create_account(
			account_name="_Test Account Shipping Charges",
			parent_account="Cash In Hand - _TC",
			company="_Test Company",
			account_currency="INR",
			account_type="Chargeable",
		)
		create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")
		create_shipping_rule(shipping_rule_type="Selling", shipping_rule_name="_Test Shipping Rule")

		fiscal_year = get_fiscal_year(date=nowdate(), company="_Test Company")
		create_tax_withholding_category(
			category_name="Test - TCS - 194C - Company",
			rate=2,
			from_date=fiscal_year[1],
			to_date=fiscal_year[2],
			account="_Test TCS Payable - _TC",
			single_threshold=30000,
			cumulative_threshold=100000,
			consider_party_ledger_amount=1,
		)
		if frappe.db.exists("Tax Withholding Category", "Test - TCS - 194C - Company"):
			twh = frappe.get_doc("Tax Withholding Category", "Test - TCS - 194C - Company")
			if twh.rates:
				twh.rates[0].from_date = fiscal_year[1]
				twh.rates[0].to_date = fiscal_year[2]
				twh.save()
		customer = frappe.get_doc("Customer", "_Test Customer")

		if not frappe.db.exists("Tax Withholding Category", "Test - TDS - 194C - Company"):
			twc_doc = frappe.new_doc("Tax Withholding Category")
			twc_doc.name = "Test - TDS - 194C - Company"
			twc_doc.category_name = "Test - TDS - 194C - Company"
			twc_doc.default = 0
			twc_doc.append(
				"rates",
				{
					"from_date": add_days(today(), -30),
					"to_date": add_days(today(), 60),
					"tax_withholding_rate": 2.0,
					"single_threshold": 30000.00,
					"cumulative_threshold": 100000,
				},
			)
			twc_doc.append("accounts", {"company": "_Test Company", "account": "_Test TDS Payable - _TC"})
			twc_doc.insert()

		category_doc = frappe.get_doc("Tax Withholding Category", "Test - TDS - 194C - Company")
		for rate in category_doc.rates:
			rate.from_date = add_days(today(), -30)
			rate.to_date = add_days(today(), 30)
		category_doc.save()
		if (
			not customer.tax_withholding_category
			or customer.tax_withholding_category != "Test - TCS - 194C - Company"
		):
			customer.tax_withholding_category = "Test - TCS - 194C - Company"
			customer.save()

		item = make_test_item("_Test Item 1")
		sales_invoice = create_sales_invoice(
			customer="_Test Customer",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=150000,
		)

		credit_1 = frappe.db.get_value(
			"GL Entry", {"voucher_no": sales_invoice.name, "account": "Sales - _TC"}, "credit"
		)
		self.assertEqual(credit_1, 150000.00)

		if customer.tax_withholding_category:
			customer.load_from_db()
			customer.tax_withholding_category = ""
			customer.save()

	def test_set_indicators_TC_ACC_241(self):
		from .sales_invoice import make_sales_return

		si = create_sales_invoice()
		si.set_indicator()
		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.status, "Unpaid")

		r_si = make_sales_return(si.name)
		r_si.insert()
		r_si.submit()
		r_si.set_indicator()
		self.assertEqual(r_si.docstatus, 1)
		self.assertEqual(r_si.status, "Return")

		si_1 = create_sales_invoice()
		pe = get_payment_entry(si_1.doctype, si_1.name)
		pe.insert(ignore_permissions=1)
		pe.submit()

		si_1.load_from_db()
		si_1.set_indicator()

		self.assertEqual(si_1.docstatus, 1)
		self.assertEqual(si_1.status, "Paid")

	def test_validate_serial_against_delivery_note_TC_ACC_242(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn = create_delivery_note(do_not_save=True)
		dn.insert(ignore_permissions=True)
		dn.submit()
		self.assertEqual(dn.docstatus, 1)
		self.assertEqual(dn.status, "To Bill")

		si = make_sales_invoice(dn.name)
		si.insert(ignore_permissions=True)
		si.validate_serial_against_delivery_note()
		si.submit()
		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.status, "Unpaid")

	def test_loyalty_programs_TC_ACC_243(self):
		from erpnext.selling.doctype.customer.test_customer import get_customer_dict

		from .sales_invoice import get_loyalty_programs

		customer = frappe.get_doc(get_customer_dict("__Test Loyalty Customer 1")).insert(
			ignore_permissions=True
		)
		customer.loyalty_program = create_loyalty_program()
		customer.save()

		loyalty_program = get_loyalty_programs(customer.name)
		self.assertEqual(loyalty_program[0], "__Test Single Loyalty 1")

		l1_program = frappe.get_doc("Loyalty Program", create_loyalty_program())
		l1_program.auto_opt_in = 1
		l1_program.save()

	def test_create_invoice_discounting_TC_ACC_244(self):
		from .sales_invoice import create_invoice_discounting

		if not frappe.db.exists("Accounting Dimension", "Branch"):
			get_dimensions = frappe.get_doc({
				"doctype": "Accounting Dimension",
				"document_type": "Branch",
				"name": "Branch"
			}).insert()
		else:
			get_dimensions = frappe.get_doc("Accounting Dimension", "Branch")
		if get_dimensions:
			get_dimensions.disabled = 1
			get_dimensions.save()
		si = create_sales_invoice()

		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.status, "Unpaid")

		accounts = create_discounting_accounts()

		invoice_discounting = create_invoice_discounting(si.name)
		invoice_discounting.loan_start_date = today()
		invoice_discounting.loan_period = 100
		invoice_discounting.short_term_loan = accounts.get("short_term_loan")
		invoice_discounting.bank_account = accounts.get("bank_account")
		invoice_discounting.bank_charges_account = accounts.get("bank_charges_account")
		invoice_discounting.accounts_receivable_credit = accounts.get("ar_credit")
		invoice_discounting.accounts_receivable_discounted = accounts.get("ar_discounted")
		invoice_discounting.accounts_receivable_unpaid = accounts.get("ar_unpaid")
		invoice_discounting.insert(ignore_permissions=True)
		invoice_discounting.submit()

		self.assertEqual(invoice_discounting.docstatus, 1)
		self.assertEqual(invoice_discounting.status, "Sanctioned")

		get_dimensions.disabled = 0
		get_dimensions.save()

	def test_get_warehouse_TC_ACC_245(self):
		si = create_sales_invoice(do_not_save=1)
		si.insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError) as cm:
			si.get_warehouse()
		self.assertIn("POS Profile required to make POS Entry", str(cm.exception))

	def test_validate_warehouse_TC_ACC_246(self):
		si = create_sales_invoice(do_not_save=1)
		si.update_stock = 1
		si.items[0].warehouse = ""

		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert(ignore_permissions=True)
		self.assertIn(f"Warehouse required for stock Item {si.items[0].item_code}", str(cm.exception))

	@change_settings("Selling Settings", {"so_required": "Yes"})
	def test_so_required_in_si_TC_ACC_247(self):
		si = create_sales_invoice(do_not_save=1)

		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert(ignore_permissions=True)
		self.assertIn(f"Sales Order is mandatory for Item {si.items[0].item_code}", str(cm.exception))

	def test_validate_item_cost_centers_TC_ACC_248(self):
		si = create_sales_invoice(do_not_save=1)
		si.items[0].cost_center = "Main - _TC1"

		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert()
		self.assertIn(
			f"Row #{si.items[0].idx}: Cost Center {si.items[0].cost_center} does not belong to company {si.company}",
			str(cm.exception),
		)

	def test_get_list_context_TC_ACC_249(self):
		from .sales_invoice import get_list_context

		data = get_list_context()
		self.assertTrue(data.get("title"), "Invoices")
		self.assertTrue(data.get("no_breadcrumbs"), True)
		self.assertTrue(data.get("show_sidebar"), True)
		self.assertTrue(data.get("show_search"), True)

	def test_set_pos_fields_TC_ACC_250(self):
		from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

		pos = make_pos_profile(do_not_insert=1)
		pos.account_for_change_amount = "Cash - _TC"
		pos.insert(ignore_permissions=True)
		si = create_sales_invoice(do_not_save=1)
		si.is_pos = 1
		si.pos_profile = pos.name
		si.set_pos_fields()
		si.insert()
		si.submit()
		company_abbr = si.get_company_abbr()

		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.status, "Unpaid")
		self.assertEqual(company_abbr, "_TC")

	def test_validate_delivery_note_TC_ACC_251(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn = create_delivery_note(do_not_save=1)
		dn.insert(ignore_permissions=True)
		dn.submit()

		si = make_sales_invoice(dn.name)
		si.update_stock = 1

		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert(ignore_permissions=1)

		self.assertIn(f"Stock cannot be updated against Delivery Note {dn.name}", str(cm.exception))

	def test_allow_write_off_only_on_pos_TC_ACC_252(self):
		si = create_sales_invoice(do_not_save=1)
		si.write_off_account = "Sales - _TC"
		si.insert(ignore_permissions=True)

		si.load_from_db()
		self.assertIsNone(si.write_off_account)

	def test_validate_dropship_item_TC_ACC_253(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_invoice, make_sales_order

		so = make_sales_order(do_not_save=True)
		so.items[0].delivered_by_supplier = 1
		so.items[0].supplier = "_Test Supplier"
		so.insert()
		so.submit()

		si = make_sales_invoice(so.name)
		si.update_stock = 1
		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert()
		self.assertIn("Could not update stock, invoice contains drop shipping item.", str(cm.exception))

	def test_enable_discount_accounting_TC_ACC_254(self):
		si = create_sales_invoice(do_not_save=1)
		si.insert(ignore_permissions=True)
		discounting = si.enable_discount_accounting
		self.assertEqual(
			discounting, frappe.db.get_single_value("Selling Settings", "enable_discount_accounting")
		)

	def test_validate_receivable_to_acc_TC_ACC_255(self):
		si = create_sales_invoice(do_not_save=1)
		si.debit_to = create_account(
			account_name="__Test Re Account__",
			parent_account="Accounts Receivable - _TC",
			company="_Test Company",
			account_type="Cash",
			report_type="Balance Sheet",
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert(ignore_permissions=True)
		self.assertIn(
			"Please ensure Debit To account __Test Re Account__ - _TC is a Receivable account. Change the account type to Receivable or select a different account.",
			str(cm.exception),
		)

	def test_validate_debit_to_acc_TC_ACC_256(self):
		account = create_discounting_accounts()
		si = create_sales_invoice(do_not_save=1)
		si.debit_to = account.get("report_account")
		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert(ignore_permissions=True)
		self.assertIn(
			"Please ensure Debit To account is a Balance Sheet account. You can change the parent account to a Balance Sheet account or select a different account.",
			str(cm.exception),
		)

	def test_on_recurring_TC_ACC_257(self):
		frappe.flags.in_test = True
		reference_si = create_sales_invoice(do_not_save=1)
		reference_si.insert(ignore_permissions=True)
		reference_si.submit()
		self.assertEqual(reference_si.docstatus, 1)
		self.assertEqual(reference_si.status, "Unpaid")

		auto_repeat = frappe.get_doc(
			{
				"doctype": "Auto Repeat",
				"reference_doctype": "Sales Invoice",
				"reference_document": reference_si.name,
				"frequency": "Monthly",
				"next_schedule_date": add_days(today(), 30),
			}
		)
		auto_repeat.insert(ignore_permissions=True)

		new_si = create_sales_invoice(do_not_save=1)
		new_si.insert(ignore_permissions=True)
		new_si.submit()
		new_si.on_recurring(reference_doc=reference_si, auto_repeat_doc=auto_repeat)

		self.assertEqual(new_si.docstatus, 1)
		self.assertIsNone(new_si.due_date)

	def test_make_maintenance_schedule_from_si_TC_ACC_258(self):
		from .sales_invoice import make_maintenance_schedule

		si = create_sales_invoice(do_not_save=1)
		si.insert(ignore_permissions=True)
		si.submit()

		self.assertEqual(si.docstatus, 1)
		self.assertEqual(si.status, "Unpaid")

		ms = make_maintenance_schedule(si.name)
		ms.transaction_date = today()
		ms.items[0].start_date = today()
		ms.items[0].end_date = add_days(today(), 1)
		ms.items[0].no_of_visits = 2
		ms.insert(ignore_permissions=True)
		ms.submit()

		self.assertEqual(ms.docstatus, 1)

	def test_validate_pos_TC_ACC_259(self):
		from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

		pos = make_pos_profile(do_not_insert=1)
		pos.account_for_change_amount = "Cash - _TC"
		pos.insert(ignore_permissions=True)

		si = create_sales_invoice(do_not_save=1)
		si.is_pos = 1
		si.pos_profile = pos.name
		si.write_off_amount = 1000
		si.is_return = 1
		si.taxes_and_charges = ""
		si.taxes = []
		si.items[0].qty = -1

		with self.assertRaises(frappe.ValidationError) as cm:
			si.insert(ignore_permissions=True)
		self.assertIn("Paid amount + Write Off Amount can not be greater than Grand Total", str(cm.exception))

	def test_get_all_mode_of_payments_TC_ACC_260(self):
		from .sales_invoice import get_all_mode_of_payments, get_mode_of_payment_info

		si = create_sales_invoice()
		mode_of_pmt = get_all_mode_of_payments(si)
		if mode_of_pmt:
			for row in mode_of_pmt:
				if row.get("parent") == "Cash":
					self.assertEqual(row.get("default_account"), "Cash - _TC")

		pmt_info = get_mode_of_payment_info("Cash", si.company)
		if pmt_info:
			for row_1 in pmt_info:
				if row_1.get("parent") == "Cash":
					self.assertEqual(row_1.get("default_account"), "Cash - _TC")

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_check_if_return_invoice_linked_with_payment_entry_TC_ACC_261(self):
		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.insert(ignore_permissions=True)
		si.submit()

		return_si = create_sales_invoice(rate=200, do_not_save=True)
		return_si.is_return = 1
		# return_si.return_against = si.name
		return_si.items[0].qty = -1
		return_si.insert(ignore_permissions=True)
		return_si.submit()

		pe = get_payment_entry(si.doctype, si.name)
		pe.append(
			"references",
			{
				"reference_doctype": return_si.doctype,
				"reference_name": return_si.name,
				"allocated_amount": -200,
			},
		)
		pe.insert(ignore_permissions=True)
		pe.submit()

		return_si.load_from_db()

		with self.assertRaises(frappe.ValidationError) as cm:
			return_si.cancel()
		self.assertIn(
			f"Please cancel and amend the Payment Entry {pe.name} to unallocate the amount of this Return Invoice before cancelling it.",
			str(cm.exception),
		)


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
	expected_gle = sorted(expected_gle, key=lambda x: x[0])
	gl_entries = sorted(gl_entries, key=lambda x: x["account"])

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
	si.is_internal_customer = args.is_internal_customer or 0
	si.shipping_rule = args.shipping_rule

	bundle_id = None
	if si.update_stock and (args.get("batch_no") or args.get("serial_no")):
		batches = {}
		qty = args.qty if args.qty is not None else 1
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

	if args.item_list:
		for item in args.item_list:
			si.append("items", item)

	else:
		si.append(
			"items",
			{
				"item_code": args.item or args.item_code or "_Test Item",
				"item_name": args.item_name or "_Test Item",
				"description": args.description or "_Test Item",
				"warehouse": args.warehouse or "_Test Warehouse - _TC",
				"target_warehouse": args.target_warehouse,
				"qty": args.qty if args.qty is not None else 1,
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
		si.insert(ignore_permissions=True)
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

	create_customer_group("_Test Customer Group")
	create_territory("_Test Territory")

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

	create_company(company_name="_Test Company", country="India", currency="INR", abbr="_TC")
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

	create_internal_supplier(
		supplier_name="_Test Internal Supplier 3",
		represents_company="_Test Company",
		allowed_to_interact_with="_Test Company",
	)


def create_internal_supplier(supplier_name, represents_company, allowed_to_interact_with):
	create_supplier_group("_Test Supplier Group")
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
		supplier.insert(ignore_permissions=True)
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
	frappe.db.set_value("Company", "_Test Company", "stock_adjustment_account", "Cost of Goods Sold - _TC")


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


def create_customer(**args):
	if not frappe.db.exists("Customer", args.get("customer_name")):
		customer = frappe.new_doc("Customer")
		customer.customer_name = args.get("customer_name")
		customer.type = "Individual"

		if args.get("company"):
			# Set company in child table `companies`
			customer.append("companies", {"company": args.get("company")})

		if args.get("currency"):
			customer.default_currency = args.get("currency")
		if args.get("company") and args.get("account"):
			customer.append("accounts", {"company": args.get("company"), "account": args.get("account")})
		customer.save()
	else:
		customer = frappe.get_doc("Customer", args.get("customer_name"))

		# Ensure the company isn't already in the child table
		if args.get("company") and not any(c.company == args.get("company") for c in customer.companies):
			customer.append("companies", {"company": args.get("company")})
			customer.save()

		return customer


def create_accounts(**args):
	if not frappe.db.exists(
		"Account", f"{args.get('account_name')} - _TC"
	):  # Ensure proper check with "- _TC"
		try:
			frappe.get_doc(
				{
					"doctype": "Account",
					"company": args.get("company") or "_Test Company",
					"account_name": args.get("account_name"),
					"parent_account": args.get("parent_account"),
					"report_type": "Balance Sheet",
					"root_type": args.get("root_type") or "Liability",
					"account_currency": args.get("account_currency") or "INR",
				}
			).insert()

		except Exception as e:
			frappe.log_error(f"Failed to insert {args.get('account_name')}", str(e))


def setup_bank_accounts():
	payment_gateway = {"doctype": "Payment Gateway", "gateway": "_Test Gateway"}

	payment_method = [
		{
			"doctype": "Payment Gateway Account",
			"is_default": 1,
			"payment_gateway": "_Test Gateway",
			"payment_account": "_Test Bank - _TC",
			"currency": "INR",
		},
		{
			"doctype": "Payment Gateway Account",
			"payment_gateway": "_Test Gateway",
			"payment_account": "_Test Bank USD - _TC",
			"currency": "USD",
		},
	]

	if not frappe.db.get_value("Payment Gateway", payment_gateway["gateway"], "name"):
		frappe.get_doc(payment_gateway).insert(ignore_permissions=True)

	for method in payment_method:
		if not frappe.db.get_value(
			"Payment Gateway Account",
			{"payment_gateway": method["payment_gateway"], "currency": method["currency"]},
			"name",
		):
			frappe.get_doc(method).insert(ignore_permissions=True)


def create_address(**args):
	if not frappe.db.exists("Address", args.get("name")):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": args.get("address_title"),
				"address_type": args.get("address_type"),
				"city": "Test Town",
				"address_line1": args.get("address_line1"),
				"is_primary_address": args.get("is_primary_address"),
				"state": args.get("state"),
				"country": args.get("country"),
				"pincode": args.get("pincode"),
			}
		).insert()
		if args.get("is_your_company_address"):
			address.append("links", {"link_doctype": "Company", "link_name": args.get("company")})
		else:
			address.append("links", {"link_doctype": args.get("doctype"), "link_name": args.get("docname")})
		address.save()

		return address


def get_months(doc):
	month_list = [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December",
	]
	idx = 1
	for m in month_list:
		mnth = doc.append("percentages")
		mnth.month = m
		mnth.percentage_allocation = 100.0 / 12
		mnth.idx = idx
		idx += 1


def create_company_and_supplier():
	fiscal_year = get_active_fiscal_year()
	parent_company = "Test Company-1122"
	child_company = "Test Company-3344"
	price_list = "Test Inter Company Transfer"
	supplier = "Test Company-1122"
	customer = "Test Company-3344"

	if not frappe.db.exists("Company", parent_company):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": parent_company,
				"abbr": "TC-1",
				"default_currency": "INR",
				"country": "India",
				"is_group": 1,
				"gstin": "27AAAAP0267H2ZN",
				"gst_category": "Registered Regular",
			}
		).insert(ignore_permissions=True)

	fiscal_year_doc = frappe.get_doc("Fiscal Year", fiscal_year)
	linked_companies = {d.company for d in fiscal_year_doc.companies}

	if parent_company not in linked_companies:
		fiscal_year_doc.append("companies", {"company": parent_company})
		fiscal_year_doc.save(ignore_permissions=True)

	if not frappe.db.exists("Company", child_company):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": child_company,
				"abbr": "TC-3",
				"default_currency": "INR",
				"country": "India",
				"gstin": "27AABCT1296R1ZN",
				"gst_category": "Registered Regular",
				"parent_company": parent_company,
			}
		).insert(ignore_permissions=True)

	if child_company not in linked_companies:
		fiscal_year_doc.append("companies", {"company": child_company})
		fiscal_year_doc.save(ignore_permissions=True)

	if not frappe.db.exists("Price List", price_list):
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": price_list,
				"currency": "INR",
				"buying": 1,
				"selling": 1,
				"countries": [{"country": "India"}],
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Supplier", supplier):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": parent_company,
				"supplier_type": "Individual",
				"country": "India",
				"default_price_list": price_list,
				"is_internal_supplier": 1,
				"represents_company": parent_company,
				"companies": [{"company": child_company}],
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": parent_company,
				"address_type": "Billing",
				"address_line1": "GP Parsik Sahakari Bank, Second Floor",
				"address_line2": "Sahkarmurti Gopinath Shivram Patil Bhavan MBT Road",
				"city": "Thane",
				"state": "Maharashtra",
				"country": "India",
				"pincode": "400605",
				"gstin": "27AAAAP0267H2ZN",
				"gst_category": "Registered Regular",
				"is_your_company_address": 1,
				"links": [
					{"link_doctype": "Company", "link_name": parent_company},
					{"link_doctype": "Supplier", "link_name": supplier},
				],
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Customer", customer):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": child_company,
				"customer_type": "Company",
				"country": "India",
				"default_price_list": price_list,
				"is_internal_customer": 1,
				"represents_company": child_company,
				"companies": [{"company": parent_company}],
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": child_company,
				"address_type": "Billing",
				"address_line1": "M1, 5, Empire Plaza Building A",
				"address_line2": "L B S Road, Off. Village Hariyali, Vikhroli West",
				"city": "Mumbai",
				"state": "Maharashtra",
				"country": "India",
				"pincode": "400083",
				"gstin": "27AABCT1296R1ZN",
				"gst_category": "Registered Regular",
				"is_your_company_address": 1,
				"links": [
					{"link_doctype": "Company", "link_name": child_company},
					{"link_doctype": "Customer", "link_name": customer},
				],
			}
		).insert(ignore_permissions=True)

	create_test_tax_data()

	return {
		"parent_company": parent_company,
		"child_company": child_company,
		"supplier": supplier,
		"customer": customer,
		"price_list": price_list,
	}


def create_test_tax_data():
	company = "Test Company-1122"
	company_abbr = "TC-1"
	child_company = "Test Company-3344"
	child_company_abbr = "TC-3"

	required_accounts_parent = [
		("Output Tax SGST", "Duties and Taxes"),
		("Output Tax CGST", "Duties and Taxes"),
	]

	required_accounts_child = [("Input Tax SGST", "Duties and Taxes"), ("Input Tax CGST", "Duties and Taxes")]

	if not frappe.db.exists("Account", f"Duties and Taxes - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Duties and Taxes",
				"parent_account": "Indirect Expenses - " + company_abbr,
				"company": company,
				"is_group": 1,
			}
		).insert()

	if not frappe.db.exists("Account", f"Duties and Taxes - {child_company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Duties and Taxes",
				"parent_account": "Indirect Expenses - " + child_company_abbr,
				"company": child_company,
				"is_group": 1,
			}
		).insert()

	for account_name, parent in required_accounts_parent:
		full_name = f"{account_name} - {company_abbr}"
		if not frappe.db.exists("Account", full_name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": f"{parent} - {company_abbr}",
					"company": company,
					"account_type": "Tax",
				}
			).insert()

	for account_name, parent in required_accounts_child:
		full_name = f"{account_name} - {child_company_abbr}"
		if not frappe.db.exists("Account", full_name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": f"{parent} - {child_company_abbr}",
					"company": child_company,
					"account_type": "Tax",
				}
			).insert()

	if not frappe.db.exists("Sales Taxes and Charges Template", "Output GST In-state - TC-1"):
		frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": "Output GST In-state",
				"company": company,
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": f"Output Tax SGST - {company_abbr}",
						"rate": 9,
						"description": f"SGST - {company_abbr}",
					},
					{
						"charge_type": "On Net Total",
						"account_head": f"Output Tax CGST - {company_abbr}",
						"rate": 9,
						"description": f"CGST - {company_abbr}",
					},
				],
			}
		).insert()

	if not frappe.db.exists("Purchase Taxes and Charges Template", "Input GST In-state - TC-1"):
		frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": "Input GST In-state",
				"company": child_company,
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": f"Input Tax CGST - {child_company_abbr}",
						"rate": 9,
						"description": f"CGST - {child_company_abbr}",
					},
					{
						"charge_type": "On Net Total",
						"account_head": f"Input Tax SGST - {child_company_abbr}",
						"rate": 9,
						"description": f"SGST - {child_company_abbr}",
					},
				],
			}
		).insert()


def get_active_fiscal_year():
	from datetime import datetime

	get_fiscal_year = frappe.db.get_value(
		"Fiscal Year",
		{"disabled": 0, "year_start_date": ["<=", today()], "year_end_date": [">=", today()]},
		pluck="name",
		order_by="creation ASC",
	)

	if not get_fiscal_year:
		current_year = datetime.today().year
		get_fiscal_year = (
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": f"{current_year}",
					"year_start_date": f"{current_year}-01-01",
					"year_end_date": f"{current_year}-12-31",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	return get_fiscal_year


def create_registered_company():
	frappe.set_user("Administrator")
	if not frappe.db.exists("Company", "_Test Indian Registered Company"):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Indian Registered Company",
				"company_type": "Company",
				"default_currency": "INR",
				"company_email": "test@example.com",
				"abbr": "_TIRC",
			}
		).insert(ignore_permissions=True)


def create_company(company_name=None, country=None, currency=None, abbr=None):
	if not frappe.db.exists("Company", company_name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"company_type": "Company",
				"default_currency": currency,
				"country": country,
				"company_email": "test@example.com",
				"abbr": abbr,
			}
		).insert()


def create_customer_group(customer_group):
	if not frappe.db.exists("Customer Group", {"customer_group_name": customer_group}):
		frappe.get_doc({"doctype": "Customer Group", "customer_group_name": customer_group}).insert(
			ignore_permissions=True
		)


def create_supplier_group(supplier_group):
	if not frappe.db.exists("Supplier Group", {"supplier_group_name": supplier_group}):
		frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": supplier_group}).insert(
			ignore_permissions=True
		)


def create_territory(territory):
	if not frappe.db.exists("Territory", {"territory_name": territory}):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": territory,
			}
		).insert(ignore_permissions=True)


def create_uom(uom):
	existing_uom = frappe.db.get_value("UOM", filters={"uom_name": uom}, fieldname="uom_name")
	if existing_uom:
		return existing_uom
	else:
		new_uom = frappe.new_doc("UOM")
		new_uom.uom_name = uom
		new_uom.save()
		return new_uom.uom_name


def create_fiscal_year(company):
	from datetime import date, datetime

	import frappe

	current_date = datetime.today().date()

	matching_fy_list = frappe.get_all(
		"Fiscal Year",
		filters={
			"disabled": 0,
			"year_start_date": ["<=", current_date],
			"year_end_date": [">=", current_date],
		},
		fields=["name", "year_start_date", "year_end_date"],
	)
	is_company = False
	if len(matching_fy_list) > 0:
		for fy in matching_fy_list:
			fiscal_year = frappe.get_doc("Fiscal Year", fy["name"])
			for years in fiscal_year.companies:
				if years.company == company:
					is_company = True
					break
			if is_company:
				break

		if not is_company:
			for rows in matching_fy_list:
				try:
					fiscal_year = frappe.get_doc("Fiscal Year", rows.name)
					fiscal_year.append("companies", {"company": company})
					fiscal_year.save()
					break
				except Exception as e:
					print(f"Failed to get Fiscal Year {fy['name']}: {e}")
					continue

	else:
		# No fiscal year includes current date — create a new one
		current_year = current_date.year
		first_date = date(current_year, 1, 1)
		last_date = date(current_year, 12, 31)

		fiscal_year = frappe.new_doc("Fiscal Year")
		fiscal_year.year = f"{current_year}-{company}"
		fiscal_year.year_start_date = first_date
		fiscal_year.year_end_date = last_date
		fiscal_year.company = company  # Required to avoid overlap error
		fiscal_year.append("companies", {"company": company})
		fiscal_year.save()


def create_discounting_accounts():
	ar_credit = create_account(
		account_name="_Test Accounts Receivable Credit",
		parent_account="Accounts Receivable - _TC",
		company="_Test Company",
	)
	ar_discounted = create_account(
		account_name="_Test Accounts Receivable Discounted",
		parent_account="Accounts Receivable - _TC",
		company="_Test Company",
	)
	ar_unpaid = create_account(
		account_name="_Test Accounts Receivable Unpaid",
		parent_account="Accounts Receivable - _TC",
		company="_Test Company",
	)
	short_term_loan = create_account(
		account_name="_Test Short Term Loan",
		parent_account="Source of Funds (Liabilities) - _TC",
		company="_Test Company",
	)
	bank_account = create_account(
		account_name="_Test Bank 2", parent_account="Bank Accounts - _TC", company="_Test Company"
	)
	bank_charges_account = create_account(
		account_name="_Test Bank Charges Account",
		parent_account="Expenses - _TC",
		company="_Test Company",
	)
	report_account = create_account(
		account_name="_Test Report Account_",
		parent_account="Expenses - _TC",
		company="_Test Company",
		report_type="Profit and Loss",
		account_type="Cash",
	)

	return {
		"ar_credit": ar_credit,
		"ar_discounted": ar_discounted,
		"ar_unpaid": ar_unpaid,
		"short_term_loan": short_term_loan,
		"bank_account": bank_account,
		"bank_charges_account": bank_charges_account,
		"report_account": report_account,
	}


def create_loyalty_program():
	from erpnext.buying.doctype.purchase_order.test_purchase_order import create_company

	create_company()
	loyality_program = "__Test Single Loyalty 1"
	# create a new loyalty Account
	if not frappe.db.exists("Account", "Loyalty - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Loyalty",
				"parent_account": "Direct Expenses - _TC",
				"company": "_Test Company",
				"is_group": 0,
				"account_type": "Expense Account",
			}
		).insert()

	# create a new loyalty program Single tier
	if not frappe.db.exists("Loyalty Program", loyality_program):
		frappe.get_doc(
			{
				"doctype": "Loyalty Program",
				"loyalty_program_name": "__Test Single Loyalty 1",
				"auto_opt_in": 0,
				"from_date": today(),
				"to_date": today(),
				"loyalty_program_type": "Single Tier Program",
				"conversion_factor": 1,
				"expiry_duration": 10,
				"company": "_Test Company",
				"cost_center": "Main - _TC",
				"expense_account": "Loyalty - _TC",
				"collection_rules": [{"tier_name": "Silver", "collection_factor": 1000, "min_spent": 1000}],
			}
		).insert()

	return {loyality_program}
