# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import today

from erpnext.accounts.utils import get_fiscal_year

test_dependencies = ["Supplier Group", "Customer Group"]


class TestTaxWithholdingCategory(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		# create relevant supplier, etc
		create_records()
		create_tax_withholding_category_records()

	def tearDown(self):
		cancel_invoices()

	def test_cumulative_threshold_tds(self):
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier", "tax_withholding_category", "Cumulative Threshold TDS"
		)
		invoices = []

		# create invoices for lower than single threshold tax rate
		for _ in range(2):
			pi = create_purchase_invoice(supplier="Test TDS Supplier")
			pi.submit()
			invoices.append(pi)

		# create another invoice whose total when added to previously created invoice,
		# surpasses cumulative threshhold
		pi = create_purchase_invoice(supplier="Test TDS Supplier")
		pi.submit()

		# assert equal tax deduction on total invoice amount until now
		self.assertEqual(pi.taxes_and_charges_deducted, 3000)
		self.assertEqual(pi.grand_total, 7000)
		invoices.append(pi)

		# TDS is already deducted, so from onward system will deduct the TDS on every invoice
		pi = create_purchase_invoice(supplier="Test TDS Supplier", rate=5000)
		pi.submit()

		# assert equal tax deduction on total invoice amount until now
		self.assertEqual(pi.taxes_and_charges_deducted, 500)
		invoices.append(pi)

		# delete invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

	def test_single_threshold_tds(self):
		invoices = []
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier1", "tax_withholding_category", "Single Threshold TDS"
		)
		pi = create_purchase_invoice(supplier="Test TDS Supplier1", rate=20000)
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes_and_charges_deducted, 2000)
		self.assertEqual(pi.grand_total, 18000)

		# check gl entry for the purchase invoice
		gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": pi.name}, fields=["*"])
		self.assertEqual(len(gl_entries), 3)
		for d in gl_entries:
			if d.account == pi.credit_to:
				self.assertEqual(d.credit, 18000)
			elif d.account == pi.items[0].get("expense_account"):
				self.assertEqual(d.debit, 20000)
			elif d.account == pi.taxes[0].get("account_head"):
				self.assertEqual(d.credit, 2000)
			else:
				raise ValueError("Account head does not match.")

		pi = create_purchase_invoice(supplier="Test TDS Supplier1")
		pi.submit()
		invoices.append(pi)

		# TDS amount is 1000 because in previous invoices it's already deducted
		self.assertEqual(pi.taxes_and_charges_deducted, 1000)

		# delete invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

	def test_tax_withholding_category_checks(self):
		invoices = []
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier3", "tax_withholding_category", "New TDS Category"
		)

		# First Invoice with no tds check
		pi = create_purchase_invoice(supplier="Test TDS Supplier3", rate=20000, do_not_save=True)
		pi.apply_tds = 0
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Second Invoice will apply TDS checked
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier3", rate=20000)
		pi1.submit()
		invoices.append(pi1)

		# Cumulative threshold is 30000
		# Threshold calculation should be on both the invoices
		# TDS should be applied only on 1000
		self.assertEqual(pi1.taxes[0].tax_amount, 1000)

		for d in reversed(invoices):
			d.cancel()

	def test_cumulative_threshold_tcs(self):
		frappe.db.set_value(
			"Customer", "Test TCS Customer", "tax_withholding_category", "Cumulative Threshold TCS"
		)
		invoices = []

		# create invoices for lower than single threshold tax rate
		for _ in range(2):
			si = create_sales_invoice(customer="Test TCS Customer")
			si.submit()
			invoices.append(si)

		# create another invoice whose total when added to previously created invoice,
		# surpasses cumulative threshold
		si = create_sales_invoice(customer="Test TCS Customer", rate=12000)
		si.submit()

		# assert tax collection on total invoice amount created until now
		tcs_charged = sum([d.base_tax_amount for d in si.taxes if d.account_head == "TCS - _TC"])
		self.assertEqual(tcs_charged, 200)
		self.assertEqual(si.grand_total, 12200)
		invoices.append(si)

		# TCS is already collected once, so going forward system will collect TCS on every invoice
		si = create_sales_invoice(customer="Test TCS Customer", rate=5000)
		si.submit()

		tcs_charged = sum(d.base_tax_amount for d in si.taxes if d.account_head == "TCS - _TC")
		self.assertEqual(tcs_charged, 500)
		invoices.append(si)

		# cancel invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

	def test_tds_calculation_on_net_total(self):
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier4", "tax_withholding_category", "Cumulative Threshold TDS"
		)
		invoices = []

		pi = create_purchase_invoice(supplier="Test TDS Supplier4", rate=20000, do_not_save=True)
		pi.append(
			"taxes",
			{
				"category": "Total",
				"charge_type": "Actual",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "Main - _TC",
				"tax_amount": 1000,
				"description": "Test",
				"add_deduct_tax": "Add",
			},
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Second Invoice will apply TDS checked
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier4", rate=20000)
		pi1.submit()
		invoices.append(pi1)

		self.assertEqual(pi1.taxes[0].tax_amount, 4000)

		# cancel invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

	def test_tds_calculation_on_net_total_partial_tds(self):
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier4", "tax_withholding_category", "Cumulative Threshold TDS"
		)
		invoices = []

		pi = create_purchase_invoice(supplier="Test TDS Supplier4", rate=20000, do_not_save=True)
		pi.extend(
			"items",
			[
				{
					"doctype": "Purchase Invoice Item",
					"item_code": frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name"),
					"qty": 1,
					"rate": 20000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 0,
				},
				{
					"doctype": "Purchase Invoice Item",
					"item_code": frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name"),
					"qty": 1,
					"rate": 35000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 1,
				},
			],
		)
		pi.save()
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes[0].tax_amount, 5500)

		# cancel invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

		orders = []

		po = create_purchase_order(supplier="Test TDS Supplier4", rate=20000, do_not_save=True)
		po.extend(
			"items",
			[
				{
					"doctype": "Purchase Order Item",
					"item_code": frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name"),
					"qty": 1,
					"rate": 20000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 0,
				},
				{
					"doctype": "Purchase Order Item",
					"item_code": frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name"),
					"qty": 1,
					"rate": 35000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
					"apply_tds": 1,
				},
			],
		)
		po.save()
		po.submit()
		orders.append(po)

		self.assertEqual(po.taxes[0].tax_amount, 5500)

		# cancel orders to avoid clashing
		for d in reversed(orders):
			d.cancel()

	def test_multi_category_single_supplier(self):
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier5", "tax_withholding_category", "Test Service Category"
		)
		invoices = []

		pi = create_purchase_invoice(supplier="Test TDS Supplier5", rate=500, do_not_save=True)
		pi.tax_withholding_category = "Test Service Category"
		pi.save()
		pi.submit()
		invoices.append(pi)

		# Second Invoice will apply TDS checked
		pi1 = create_purchase_invoice(supplier="Test TDS Supplier5", rate=2500, do_not_save=True)
		pi1.tax_withholding_category = "Test Goods Category"
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		self.assertEqual(pi1.taxes[0].tax_amount, 250)

		# cancel invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

	def test_tax_withholding_category_voucher_display(self):
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier6", "tax_withholding_category", "Test Multi Invoice Category"
		)
		invoices = []

		pi = create_purchase_invoice(supplier="Test TDS Supplier6", rate=4000, do_not_save=True)
		pi.apply_tds = 1
		pi.tax_withholding_category = "Test Multi Invoice Category"
		pi.save()
		pi.submit()
		invoices.append(pi)

		pi1 = create_purchase_invoice(supplier="Test TDS Supplier6", rate=2000, do_not_save=True)
		pi1.apply_tds = 1
		pi1.is_return = 1
		pi1.items[0].qty = -1
		pi1.tax_withholding_category = "Test Multi Invoice Category"
		pi1.save()
		pi1.submit()
		invoices.append(pi1)

		pi2 = create_purchase_invoice(supplier="Test TDS Supplier6", rate=9000, do_not_save=True)
		pi2.apply_tds = 1
		pi2.tax_withholding_category = "Test Multi Invoice Category"
		pi2.save()
		pi2.submit()
		invoices.append(pi2)

		pi2.load_from_db()

		self.assertTrue(pi2.taxes[0].tax_amount, 1100)

		self.assertTrue(pi2.tax_withheld_vouchers[0].voucher_name == pi1.name)
		self.assertTrue(pi2.tax_withheld_vouchers[0].taxable_amount == pi1.net_total)
		self.assertTrue(pi2.tax_withheld_vouchers[1].voucher_name == pi.name)
		self.assertTrue(pi2.tax_withheld_vouchers[1].taxable_amount == pi.net_total)

		# cancel invoices to avoid clashing
		for d in reversed(invoices):
			d.cancel()

	def test_tax_withholding_via_payment_entry_for_advances(self):
		frappe.db.set_value(
			"Supplier", "Test TDS Supplier7", "tax_withholding_category", "Advance TDS Category"
		)

		# create payment entry
		pe1 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier7", paid_amount=4000
		)
		pe1.submit()

		self.assertFalse(pe1.get("taxes"))

		pe2 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier7", paid_amount=4000
		)
		pe2.submit()

		self.assertFalse(pe2.get("taxes"))

		pe3 = create_payment_entry(
			payment_type="Pay", party_type="Supplier", party="Test TDS Supplier7", paid_amount=4000
		)
		pe3.apply_tax_withholding_amount = 1
		pe3.save()
		pe3.submit()

		self.assertEquals(pe3.get("taxes")[0].tax_amount, 1200)
		pe1.cancel()
		pe2.cancel()
		pe3.cancel()


def cancel_invoices():
	purchase_invoices = frappe.get_all(
		"Purchase Invoice",
		{
			"supplier": ["in", ["Test TDS Supplier", "Test TDS Supplier1", "Test TDS Supplier2"]],
			"docstatus": 1,
		},
		pluck="name",
	)

	sales_invoices = frappe.get_all(
		"Sales Invoice", {"customer": "Test TCS Customer", "docstatus": 1}, pluck="name"
	)

	for d in purchase_invoices:
		frappe.get_doc("Purchase Invoice", d).cancel()

	for d in sales_invoices:
		frappe.get_doc("Sales Invoice", d).cancel()


def create_purchase_invoice(**args):
	# return sales invoice doc object
	item = frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name")

	args = frappe._dict(args)
	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"posting_date": today(),
			"apply_tds": 0 if args.do_not_apply_tds else 1,
			"supplier": args.supplier,
			"company": "_Test Company",
			"taxes_and_charges": "",
			"currency": "INR",
			"credit_to": "Creditors - _TC",
			"taxes": [],
			"items": [
				{
					"doctype": "Purchase Invoice Item",
					"item_code": item,
					"qty": args.qty or 1,
					"rate": args.rate or 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
				}
			],
		}
	)

	pi.save()
	return pi


def create_purchase_order(**args):
	# return purchase order doc object
	item = frappe.db.get_value("Item", {"item_name": "TDS Item"}, "name")

	args = frappe._dict(args)
	po = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"transaction_date": today(),
			"schedule_date": today(),
			"apply_tds": 0 if args.do_not_apply_tds else 1,
			"supplier": args.supplier,
			"company": "_Test Company",
			"taxes_and_charges": "",
			"currency": "INR",
			"taxes": [],
			"items": [
				{
					"doctype": "Purchase Order Item",
					"item_code": item,
					"qty": args.qty or 1,
					"rate": args.rate or 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Stock Received But Not Billed - _TC",
				}
			],
		}
	)

	po.save()
	return po


def create_sales_invoice(**args):
	# return sales invoice doc object
	item = frappe.db.get_value("Item", {"item_name": "TCS Item"}, "name")

	args = frappe._dict(args)
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"posting_date": today(),
			"customer": args.customer,
			"company": "_Test Company",
			"taxes_and_charges": "",
			"currency": "INR",
			"debit_to": "Debtors - _TC",
			"taxes": [],
			"items": [
				{
					"doctype": "Sales Invoice Item",
					"item_code": item,
					"qty": args.qty or 1,
					"rate": args.rate or 10000,
					"cost_center": "Main - _TC",
					"expense_account": "Cost of Goods Sold - _TC",
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
				}
			],
		}
	)

	si.save()
	return si


def create_payment_entry(**args):
	# return payment entry doc object
	args = frappe._dict(args)
	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"posting_date": today(),
			"payment_type": args.payment_type,
			"party_type": args.party_type,
			"party": args.party,
			"company": "_Test Company",
			"paid_from": "Cash - _TC",
			"paid_to": "Creditors - _TC",
			"paid_amount": args.paid_amount or 10000,
			"received_amount": args.paid_amount or 10000,
			"reference_no": args.reference_no or "12345",
			"reference_date": today(),
			"paid_from_account_currency": "INR",
			"paid_to_account_currency": "INR",
		}
	)

	pe.save()
	return pe


def create_records():
	# create a new suppliers
	for name in [
		"Test TDS Supplier",
		"Test TDS Supplier1",
		"Test TDS Supplier2",
		"Test TDS Supplier3",
		"Test TDS Supplier4",
		"Test TDS Supplier5",
		"Test TDS Supplier6",
		"Test TDS Supplier7",
	]:
		if frappe.db.exists("Supplier", name):
			continue

		frappe.get_doc(
			{
				"supplier_group": "_Test Supplier Group",
				"supplier_name": name,
				"doctype": "Supplier",
			}
		).insert()

	for name in ["Test TCS Customer"]:
		if frappe.db.exists("Customer", name):
			continue

		frappe.get_doc(
			{"customer_group": "_Test Customer Group", "customer_name": name, "doctype": "Customer"}
		).insert()

	# create item
	if not frappe.db.exists("Item", "TDS Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "TDS Item",
				"item_name": "TDS Item",
				"item_group": "All Item Groups",
				"is_stock_item": 0,
			}
		).insert()

	if not frappe.db.exists("Item", "TCS Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "TCS Item",
				"item_name": "TCS Item",
				"item_group": "All Item Groups",
				"is_stock_item": 1,
			}
		).insert()

	# create tds account
	if not frappe.db.exists("Account", "TDS - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": "_Test Company",
				"account_name": "TDS",
				"parent_account": "Tax Assets - _TC",
				"report_type": "Balance Sheet",
				"root_type": "Asset",
			}
		).insert()

	# create tcs account
	if not frappe.db.exists("Account", "TCS - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": "_Test Company",
				"account_name": "TCS",
				"parent_account": "Duties and Taxes - _TC",
				"report_type": "Balance Sheet",
				"root_type": "Liability",
			}
		).insert()


def create_tax_withholding_category_records():
	fiscal_year = get_fiscal_year(today(), company="_Test Company")
	from_date = fiscal_year[1]
	to_date = fiscal_year[2]

	# Cumulative threshold
	create_tax_withholding_category(
		category_name="Cumulative Threshold TDS",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=0,
		cumulative_threshold=30000.00,
	)

	# Category for TCS
	create_tax_withholding_category(
		category_name="Cumulative Threshold TCS",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TCS - _TC",
		single_threshold=0,
		cumulative_threshold=30000.00,
	)

	# Single threshold
	create_tax_withholding_category(
		category_name="Single Threshold TDS",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=20000,
		cumulative_threshold=0,
	)

	create_tax_withholding_category(
		category_name="New TDS Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=0,
		cumulative_threshold=30000,
		round_off_tax_amount=1,
		consider_party_ledger_amount=1,
		tax_on_excess_amount=1,
	)

	create_tax_withholding_category(
		category_name="Test Service Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=2000,
		cumulative_threshold=2000,
	)

	create_tax_withholding_category(
		category_name="Test Goods Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=2000,
		cumulative_threshold=2000,
	)

	create_tax_withholding_category(
		category_name="Test Multi Invoice Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=5000,
		cumulative_threshold=10000,
	)

	create_tax_withholding_category(
		category_name="Advance TDS Category",
		rate=10,
		from_date=from_date,
		to_date=to_date,
		account="TDS - _TC",
		single_threshold=5000,
		cumulative_threshold=10000,
		consider_party_ledger_amount=1,
	)


def create_tax_withholding_category(
	category_name,
	rate,
	from_date,
	to_date,
	account,
	single_threshold=0,
	cumulative_threshold=0,
	round_off_tax_amount=0,
	consider_party_ledger_amount=0,
	tax_on_excess_amount=0,
):
	if not frappe.db.exists("Tax Withholding Category", category_name):
		frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"name": category_name,
				"category_name": category_name,
				"round_off_tax_amount": round_off_tax_amount,
				"consider_party_ledger_amount": consider_party_ledger_amount,
				"tax_on_excess_amount": tax_on_excess_amount,
				"rates": [
					{
						"from_date": from_date,
						"to_date": to_date,
						"tax_withholding_rate": rate,
						"single_threshold": single_threshold,
						"cumulative_threshold": cumulative_threshold,
					}
				],
				"accounts": [{"company": "_Test Company", "account": account}],
			}
		).insert()
