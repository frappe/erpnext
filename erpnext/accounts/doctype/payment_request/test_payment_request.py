# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import re
import unittest

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
	create_company,
	create_payment_terms_template,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
	get_amount,
	get_open_payment_requests_query,
	get_print_format_list,
	make_payment_entry,
	make_payment_order,
	make_payment_request,
)
from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.subscription.test_subscription import create_subscription
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import create_customer

test_dependencies = ["Currency Exchange", "Journal Entry", "Contact", "Address"]
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


class TestPaymentRequest(FrappeTestCase):
	def setUp(self):
		if not frappe.db.get_value("Payment Gateway", payment_gateway["gateway"], "name"):
			frappe.get_doc(payment_gateway).insert(ignore_permissions=True)

		for method in payment_method:
			if not frappe.db.get_value(
				"Payment Gateway Account",
				{"payment_gateway": method["payment_gateway"], "currency": method["currency"]},
				"name",
			):
				frappe.get_doc(method).insert(ignore_permissions=True)

	def test_payment_request_linkings(self):
		so_inr = make_sales_order(currency="INR", do_not_save=True)
		so_inr.disable_rounded_total = 1
		so_inr.save()

		pr = make_payment_request(
			dt="Sales Order",
			dn=so_inr.name,
			recipient_id="saurabh@erpnext.com",
			payment_gateway_account="_Test Gateway - INR",
		)

		self.assertEqual(pr.reference_doctype, "Sales Order")
		self.assertEqual(pr.reference_name, so_inr.name)
		self.assertEqual(pr.currency, "INR")

		conversion_rate = get_exchange_rate("USD", "INR")

		si_usd = create_sales_invoice(currency="USD", conversion_rate=conversion_rate)
		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si_usd.name,
			recipient_id="saurabh@erpnext.com",
			payment_gateway_account="_Test Gateway - USD",
		)

		self.assertEqual(pr.reference_doctype, "Sales Invoice")
		self.assertEqual(pr.reference_name, si_usd.name)
		self.assertEqual(pr.currency, "USD")

	def test_payment_entry_against_purchase_invoice(self):
		si_usd = make_purchase_invoice(
			supplier="_Test Supplier USD",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Purchase Invoice",
			dn=si_usd.name,
			party_type="Supplier",
			party="_Test Supplier USD",
			recipient_id="user@example.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			submit_doc=1,
			return_doc=1,
		)

		pr.create_payment_entry()
		pr.load_from_db()

		self.assertEqual(pr.status, "Paid")

	def test_multiple_payment_entry_against_purchase_invoice(self):
		purchase_invoice = make_purchase_invoice(
			supplier="_Test Supplier USD",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Purchase Invoice",
			party_type="Supplier",
			party="_Test Supplier USD",
			dn=purchase_invoice.name,
			recipient_id="user@example.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			return_doc=1,
		)

		pr.grand_total = pr.grand_total / 2

		pr.submit()
		pr.create_payment_entry()

		purchase_invoice.load_from_db()
		self.assertEqual(purchase_invoice.status, "Partly Paid")

		pr = make_payment_request(
			dt="Purchase Invoice",
			party_type="Supplier",
			party="_Test Supplier USD",
			dn=purchase_invoice.name,
			recipient_id="user@example.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			return_doc=1,
		)

		pr.save()
		pr.submit()
		pr.create_payment_entry()

		purchase_invoice.load_from_db()
		self.assertEqual(purchase_invoice.status, "Paid")

	def test_payment_entry(self):
		frappe.db.set_value(
			"Company", "_Test Company", "exchange_gain_loss_account", "_Test Exchange Gain/Loss - _TC"
		)
		frappe.db.set_value("Company", "_Test Company", "write_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "cost_center", "_Test Cost Center - _TC")

		so_inr = make_sales_order(currency="INR")
		pr = make_payment_request(
			dt="Sales Order",
			dn=so_inr.name,
			recipient_id="saurabh@erpnext.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - INR",
			submit_doc=1,
			return_doc=1,
		)
		pe = pr.set_as_paid()

		so_inr = frappe.get_doc("Sales Order", so_inr.name)

		self.assertEqual(so_inr.advance_paid, 1000)

		si_usd = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si_usd.name,
			recipient_id="saurabh@erpnext.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			submit_doc=1,
			return_doc=1,
		)

		pe = pr.set_as_paid()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 5000, si_usd.name],
				[pr.payment_account, 5000.0, 0, None],
			]
		)

		gl_entries = frappe.db.sql(
			"""select account, debit, credit, against_voucher
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			pe.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[gle.account][0], gle.account)
			self.assertEqual(expected_gle[gle.account][1], gle.debit)
			self.assertEqual(expected_gle[gle.account][2], gle.credit)
			self.assertEqual(expected_gle[gle.account][3], gle.against_voucher)

	def test_status(self):
		si_usd = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si_usd.name,
			recipient_id="saurabh@erpnext.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			submit_doc=1,
			return_doc=1,
		)

		pe = pr.create_payment_entry()
		pr.load_from_db()

		self.assertEqual(pr.status, "Paid")

		pe.cancel()
		pr.load_from_db()

		self.assertEqual(pr.status, "Requested")

	def test_multiple_payment_entries_against_sales_order(self):
		# Make Sales Order, grand_total = 1000
		so = make_sales_order()

		# Payment Request amount = 200
		pr1 = make_payment_request(
			dt="Sales Order", dn=so.name, recipient_id="nabin@erpnext.com", return_doc=1
		)
		pr1.grand_total = 200
		pr1.submit()

		# Make a 2nd Payment Request
		pr2 = make_payment_request(
			dt="Sales Order", dn=so.name, recipient_id="nabin@erpnext.com", return_doc=1
		)

		self.assertEqual(pr2.grand_total, 800)

		# Try to make Payment Request more than SO amount, should give validation
		pr2.grand_total = 900
		self.assertRaises(frappe.ValidationError, pr2.save)

	def test_conversion_on_foreign_currency_accounts(self):
		po_doc = create_purchase_order(supplier="_Test Supplier USD", currency="USD", do_not_submit=1)
		po_doc.conversion_rate = 80
		po_doc.items[0].qty = 1
		po_doc.items[0].rate = 10
		po_doc.save().submit()

		pr = make_payment_request(dt=po_doc.doctype, dn=po_doc.name, recipient_id="nabin@erpnext.com")
		pr = frappe.get_doc(pr).save().submit()

		pe = pr.create_payment_entry()
		self.assertEqual(pe.base_paid_amount, 800)
		self.assertEqual(pe.paid_amount, 800)
		self.assertEqual(pe.base_received_amount, 800)
		self.assertEqual(pe.received_amount, 10)

	def test_multiple_payment_if_partially_paid_for_same_currency(self):
		so = make_sales_order(currency="INR", qty=1, rate=1000)
		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		self.assertEqual(pr.grand_total, 1000)
		self.assertEqual(pr.outstanding_amount, pr.grand_total)
		self.assertEqual(pr.party_account_currency, pr.currency)  # INR
		so.load_from_db()
		# to make partial payment
		pe = pr.create_payment_entry(submit=False)
		pe.paid_amount = 200
		pe.references[0].allocated_amount = 200
		pe.submit()
		self.assertEqual(pe.references[0].payment_request, pr.name)
		so.load_from_db()
		pr.load_from_db()
		self.assertEqual(pr.status, "Partially Paid")
		self.assertEqual(pr.outstanding_amount, 800)
		self.assertEqual(pr.grand_total, 1000)
		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Request is already created"),
			make_payment_request,
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		# complete payment
		pe = pr.create_payment_entry()
		self.assertEqual(pe.paid_amount, 800)  # paid amount set from pr's outstanding amount
		self.assertEqual(pe.references[0].allocated_amount, 800)
		self.assertEqual(pe.references[0].outstanding_amount, 800)  # for Orders it is not zero
		self.assertEqual(pe.references[0].payment_request, pr.name)
		so.load_from_db()
		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 1000)
		# creating a more payment Request must not allowed
		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Entry is already created"),
			make_payment_request,
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

	@change_settings("Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1})
	def test_multiple_payment_if_partially_paid_for_multi_currency(self):
		pi = make_purchase_invoice(currency="USD", conversion_rate=50, qty=1, rate=100, do_not_save=1)
		pi.credit_to = "Creditors - _TC"
		pi.submit()
		pr = make_payment_request(
			dt="Purchase Invoice",
			dn=pi.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		# 100 USD -> 5000 INR
		self.assertEqual(pr.grand_total, 100)
		self.assertEqual(pr.outstanding_amount, 5000)
		self.assertEqual(pr.currency, "USD")
		self.assertEqual(pr.party_account_currency, "INR")
		self.assertEqual(pr.status, "Initiated")
		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Request is already created"),
			make_payment_request,
			dt="Purchase Invoice",
			dn=pi.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		# to make partial payment
		pe = pr.create_payment_entry(submit=False)
		pe.paid_amount = 2000
		pe.references[0].allocated_amount = 2000
		pe.submit()
		self.assertEqual(pe.references[0].payment_request, pr.name)
		pr.load_from_db()
		self.assertEqual(pr.status, "Partially Paid")
		self.assertEqual(pr.outstanding_amount, 3000)
		self.assertEqual(pr.grand_total, 100)
		# complete payment
		pe = pr.create_payment_entry()
		self.assertEqual(pe.paid_amount, 3000)  # paid amount set from pr's outstanding amount
		self.assertEqual(pe.references[0].allocated_amount, 3000)
		self.assertEqual(pe.references[0].outstanding_amount, 0)  # for Invoices it will zero
		self.assertEqual(pe.references[0].payment_request, pr.name)
		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 100)
		# creating a more payment Request must not allowed
		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Entry is already created"),
			make_payment_request,
			dt="Purchase Invoice",
			dn=pi.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

	def test_single_payment_with_payment_term_for_same_currency(self):
		create_payment_terms_template()
		po = create_purchase_order(do_not_save=1, currency="INR", qty=1, rate=20000)
		po.payment_terms_template = "Test Receivable Template"  # 84.746 and 15.254
		po.save()
		po.submit()
		pr = make_payment_request(
			dt="Purchase Order",
			dn=po.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		self.assertEqual(pr.grand_total, 20000)
		self.assertEqual(pr.outstanding_amount, pr.grand_total)
		self.assertEqual(pr.party_account_currency, pr.currency)  # INR
		self.assertEqual(pr.status, "Initiated")
		po.load_from_db()
		pe = pr.create_payment_entry()
		self.assertEqual(len(pe.references), 2)
		self.assertEqual(pe.paid_amount, 20000)
		# check 1st payment term
		self.assertEqual(pe.references[0].allocated_amount, 16949.2)
		self.assertEqual(pe.references[0].payment_request, pr.name)
		# check 2nd payment term
		self.assertEqual(pe.references[1].allocated_amount, 3050.8)
		self.assertEqual(pe.references[1].payment_request, pr.name)
		po.load_from_db()
		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 20000)

	@change_settings("Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1})
	def test_single_payment_with_payment_term_for_multi_currency(self):
		create_payment_terms_template()
		si = create_sales_invoice(
			do_not_save=1, currency="USD", debit_to="Debtors - _TC", qty=1, rate=200, conversion_rate=50
		)
		si.payment_terms_template = "Test Receivable Template"  # 84.746 and 15.254
		si.save()
		si.submit()
		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		# 200 USD -> 10000 INR
		self.assertEqual(pr.grand_total, 200)
		self.assertEqual(pr.outstanding_amount, 10000)
		self.assertEqual(pr.currency, "USD")
		self.assertEqual(pr.party_account_currency, "INR")
		pe = pr.create_payment_entry()
		self.assertEqual(len(pe.references), 2)
		self.assertEqual(pe.paid_amount, 10000)
		# check 1st payment term
		# convert it via dollar and conversion_rate
		self.assertEqual(pe.references[0].allocated_amount, 8474.5)  # multi currency conversion
		self.assertEqual(pe.references[0].payment_request, pr.name)
		# check 2nd payment term
		self.assertEqual(pe.references[1].allocated_amount, 1525.5)  # multi currency conversion
		self.assertEqual(pe.references[1].payment_request, pr.name)
		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 200)

	def test_payment_cancel_process(self):
		so = make_sales_order(currency="INR", qty=1, rate=1000)
		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		self.assertEqual(pr.grand_total, 1000)
		self.assertEqual(pr.outstanding_amount, pr.grand_total)
		so.load_from_db()
		pe = pr.create_payment_entry(submit=False)
		pe.paid_amount = 800
		pe.references[0].allocated_amount = 800
		pe.submit()
		self.assertEqual(pe.references[0].payment_request, pr.name)
		so.load_from_db()
		pr.load_from_db()
		self.assertEqual(pr.status, "Partially Paid")
		self.assertEqual(pr.outstanding_amount, 200)
		self.assertEqual(pr.grand_total, 1000)
		# cancelling PE
		pe.cancel()
		pr.load_from_db()
		self.assertEqual(pr.status, "Requested")
		self.assertEqual(pr.outstanding_amount, 1000)
		self.assertEqual(pr.grand_total, 1000)
		so.load_from_db()

	def test_partial_paid_invoice_with_payment_request(self):
		si = create_sales_invoice(currency="INR", qty=1, rate=5000)
		si.save()
		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "PAYEE0002"
		pe.reference_date = frappe.utils.nowdate()
		pe.paid_amount = 2500
		pe.references[0].allocated_amount = 2500
		pe.save()
		pe.submit()

		si.load_from_db()
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1)

		self.assertEqual(pr.grand_total, si.outstanding_amount)

	def test_partial_paid_invoice_with_more_payment_entry(self):
		pi = make_purchase_invoice(currency="INR", qty=1, rate=500)
		pi.submit()
		pi_1 = make_purchase_invoice(currency="INR", qty=1, rate=300)
		pi_1.submit()

		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 200
		pr.submit()
		pr.create_payment_entry()
		pr_1 = make_payment_request(
			dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1
		)
		pr_1.grand_total = 200
		pr_1.submit()
		pr_1.create_payment_entry()

		pe = get_payment_entry(dt="Purchase Invoice", dn=pi.name)
		pe.paid_amount = 200
		pe.references[0].reference_doctype = pi.doctype
		pe.references[0].reference_name = pi.name
		pe.references[0].grand_total = pi.grand_total
		pe.references[0].outstanding_amount = pi.outstanding_amount
		pe.references[0].allocated_amount = 100
		pe.append(
			"references",
			{
				"reference_doctype": pi_1.doctype,
				"reference_name": pi_1.name,
				"grand_total": pi_1.grand_total,
				"outstanding_amount": pi_1.outstanding_amount,
				"allocated_amount": 100,
			},
		)

		pr_2 = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1)
		pi.load_from_db()
		self.assertEqual(pr_2.grand_total, pi.outstanding_amount)

	def test_validate_payment_request_amount_TC_ACC_146(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 2, "rate": 50})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 100)

		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 0
		with self.assertRaises(frappe.ValidationError, msg="Amount cannot be zero"):
			pr.save()

	def test_validate_reference_document_TC_ACC_147(self):
		pr = frappe.new_doc("Payment Request")
		pr.payment_request_type = "Outward"
		pr.reference_doctype = ""
		pr.reference_name = ""
		pr.grand_total = 500
		self.assertEqual(pr.reference_doctype, "")
		self.assertEqual(pr.reference_name, "")
		with self.assertRaises(
			frappe.ValidationError, msg="To create a Payment Request reference document is required"
		):
			pr.save()

	def test_validate_payment_entry_already_created_TC_ACC_148(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		customer = create_customer()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		item = create_item(item_code=item_code, valuation_rate=100)
		so = frappe.get_doc(
			dict(
				doctype="Sales Order",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				delivery_date=add_days(today(), 2),
				order_type="Sales",
			)
		)

		so.append("items", {"item_code": item.item_code, "qty": 3, "rate": 50})
		so.save()
		so.submit()
		self.assertEqual(so.customer, customer)
		pr = make_payment_request(dt="Sales Order", dn=so.name, mute_email=1, submit_doc=1, return_doc=1)
		self.assertEqual(pr.reference_name, so.name)
		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company=company,
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		pr.create_payment_entry()
		pr.reload()
		self.assertEqual(pr.status, "Paid")
		pr_1 = frappe.get_doc(
			dict(
				doctype="Payment Request",
				payment_request_type="Inward",
				company=company,
				party_type="Customer",
				party=customer,
				reference_doctype="Sales Order",
				reference_name=so.name,
			)
		)
		with self.assertRaises(frappe.ValidationError, msg="Payment Entry is already created"):
			pr_1.save()

	def test_validate_subscription_details_TC_ACC_149(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		customer = create_customer()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		item = create_item(item_code=item_code, valuation_rate=100)
		so = frappe.get_doc(
			dict(
				doctype="Sales Order",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				delivery_date=add_days(today(), 2),
			)
		)

		so.append("items", {"item_code": item.item_code, "qty": 3, "rate": 50})
		so.save()
		so.submit()
		self.assertEqual(so.customer, customer)
		pg = create_payment_gateway_account("GooglePay")
		sp_name = "_TestGooglePay"
		sp = create_subscription_plan(
			sp_name,
			plan_name="_TestSp",
			subscription_based_on="Fixed Rate",
			cost=100,
			item_code=item.item_code,
			payment_gateway=pg.name,
			payment_channel="Email",
		)
		pr = make_payment_request(dt="Sales Order", dn=so.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 150
		pr.is_a_subscription = 1
		pr.append("subscription_plans", {"plan": sp.name, "qty": 3})
		with self.assertRaises(frappe.ValidationError) as context:
			pr.save()
		self.assertIn("The payment gateway account in plan", str(context.exception))
		pr.reload()
		pr.grand_total = 150
		pr.is_a_subscription = 1
		pr.append("subscription_plans", {"plan": sp.name, "qty": 3})
		pr.payment_gateway_account = pg.name
		pr.save()
		self.assertEqual(pr.payment_gateway_account, pg.name)
		self.assertEqual(pr.subscription_plans[0].plan, sp.name)

	def test_validate_exisiting_payment_request_amount_TC_ACC_150(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 2, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 200)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 100
		pr.save()
		pr.submit()
		self.assertEqual(pr.grand_total, 100)
		self.assertEqual(pr.reference_name, pi.name)
		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company=company,
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		pr.create_payment_entry(submit=False)
		pe = get_payment_entry(dt="Purchase Invoice", dn=pi.name)
		pe.paid_amount = 100
		pe.append(
			"references",
			{
				"reference_doctype": pi.doctype,
				"reference_name": pi.name,
				"grand_total": pi.grand_total,
				"outstanding_amount": pi.outstanding_amount,
				"allocated_amount": 100,
			},
		)
		self.assertEqual(pe.paid_amount, 100)
		self.assertEqual(pe.references[0].reference_name, pi.name)
		pr_1 = make_payment_request(
			dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1
		)
		pr_1.grand_total = 200
		with self.assertRaises(
			frappe.ValidationError,
			msg="Total Payment Request amount cannot be greater than Purchase Invoice amount",
		):
			pr_1.save()

	def test_payment_entry_already_exists_on_cancel_TC_ACC_151(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 4, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 400)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 400
		pr.save()
		pr.submit()
		self.assertEqual(pr.grand_total, 400)
		self.assertEqual(pr.reference_name, pi.name)
		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company=company,
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		pr.create_payment_entry()
		pe = get_payment_entry(dt="Purchase Invoice", dn=pi.name)
		pe.paid_amount = 400
		pe.append(
			"references",
			{
				"reference_doctype": pi.doctype,
				"reference_name": pi.name,
				"grand_total": pi.grand_total,
				"outstanding_amount": pi.outstanding_amount,
				"allocated_amount": 400,
			},
		)
		self.assertEqual(pe.paid_amount, 400)
		self.assertEqual(pe.references[0].reference_name, pi.name)
		pr.reload()
		self.assertEqual(pr.status, "Paid")
		with self.assertRaises(frappe.ValidationError, msg="Payment Entry already exists"):
			pr.cancel()

	def test_set_payment_request_as_cancel_TC_ACC_152(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 800)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 800
		pr.save()
		pr.submit()
		self.assertEqual(pr.grand_total, 800)
		self.assertEqual(pr.reference_name, pi.name)
		pr.reload()
		self.assertEqual(pr.status, "Initiated")
		pr.cancel()

	def test_make_invoice_TC_ACC_153(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		customer = create_customer()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		item = create_item(item_code=item_code, valuation_rate=100)
		so = frappe.get_doc(
			dict(
				doctype="Sales Order",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				delivery_date=add_days(today(), 2),
				order_type="Shopping Cart",
			)
		)

		so.append("items", {"item_code": item.item_code, "qty": 1, "rate": 1000})
		so.save()
		so.submit()
		self.assertEqual(so.customer, customer)
		pg = create_payment_gateway_account("_Test Gateway Accoun")
		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
			payment_gateway_account=pg.name,
		)
		pr.set_as_paid()
		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.reference_name, so.name)

	def test_make_payment_request_method_TC_ACC_154(self):
		frappe.set_user("Administrator")
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		loyalty_program_name = "_Test Loyalty"
		lp = create_loyalty_program(loyalty_program_name)
		customer = create_customer()
		customer_details = frappe.get_doc("Customer", customer)
		customer_details.loyalty_program = lp.name
		customer_details.save()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		item = create_item(item_code=item_code, valuation_rate=100)
		si = frappe.get_doc(
			dict(
				doctype="Sales Invoice",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				due_date=add_days(today(), 2),
				order_type="Shopping Cart",
			)
		)

		si.append("items", {"item_code": item.item_code, "qty": 1, "rate": 200})
		si.save()
		si.submit()
		self.assertEqual(si.customer, customer)
		customer_details.reload()
		so = frappe.get_doc(
			dict(
				doctype="Sales Order",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				delivery_date=add_days(today(), 2),
				order_type="Shopping Cart",
			)
		)

		so.append("items", {"item_code": item.item_code, "qty": 1, "rate": 200})
		so.save()
		so.submit()
		self.assertEqual(so.customer, customer)
		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

		create_payment_gateway_account("_Test GateWay 4", is_default=True)
		pr = make_payment_request(
			dt="Sales Order", dn=so.name, mute_email=1, submit_doc=0, return_doc=1, loyalty_points=50
		)
		pr.grand_total = 50
		pr.save()
		self.assertEqual(pr.status, "Draft")
		pr_1 = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		self.assertEqual(pr_1.reference_name, so.name)

	def test_get_amount_ref_doctype_TC_ACC_155(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		customer = create_customer()
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 2, "rate": 50})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		create_account(
			account_name="Case",
			parent_account="Cash In Hand - _TC",
			company=company,
			account_type="Cash",
			account_currency="INR",
			is_group=0,
		)
		create_account(
			account_name="_Test Write Off",
			parent_account="Indirect Expenses - _TC",
			company=company,
			account_currency="INR",
			is_group=0,
		)
		create_account(
			account_name="_Test Account Cost for Goods Sold",
			parent_account="Indirect Expenses - _TC",
			account_type="Expense Account",
			company=company,
			account_currency="INR",
			is_group=0,
		)

		purchase_invoice = frappe.get_doc("Purchase Invoice", pi.name)
		get_amount(purchase_invoice, payment_account="Case - _TC")

		create_user(email="test@example.com")
		create_price_list()
		create_cost_center(cost_center_name="_Test Write Off Cost Center")
		create_cost_center(cost_center_name="_Test Cost Center")
		mp = create_mode_of_payment(
			mode_of_payment="PhonePay", type="Phone", company=company, default_account="Cash - _TC"
		)
		test_user, pos_profile = init_user_and_profile()
		pos_profile.payments = []
		pos_profile.append("payments", {"default": 1, "mode_of_payment": mp.name})
		pos_profile.save()
		si = frappe.get_doc(
			dict(
				doctype="Sales Invoice",
				customer=customer,
				is_pos=1,
				pos_profile=pos_profile,
				currency="INR",
				company=company,
			)
		)
		si.append("payments", {"mode_of_payment": mp.name, "account": "Cash - _TC", "amount": 2000})
		si.append("items", {"item_code": item.item_code, "qty": 4, "rate": 500})
		si.save()
		si.submit()
		get_amount(si, payment_account="Cash - _TC")

		opening_entry = create_opening_entry(pos_profile=pos_profile, user=test_user.name)
		self.assertEqual(opening_entry.status, "Open")
		pos_inv = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv.payments = []
		pos_inv.append("payments", {"mode_of_payment": mp.name, "account": "Cash - _TC", "amount": 3500})
		pos_inv.save()
		pos_doc = frappe.get_doc("POS Invoice", pos_inv.name)
		get_amount(pos_doc, payment_account="Cash - _TC")

	def test_get_print_format_TC_ACC_156(self):
		get_print_format_list("Payment Request")

	def test_make_payment_entry_TC_ACC_157(self):
		frappe.set_user("Administrator")
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 800)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 800
		pr.save()
		pr.submit()
		self.assertEqual(pr.grand_total, 800)
		self.assertEqual(pr.reference_name, pi.name)
		pr.reload()
		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company=company,
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		make_payment_entry(docname=pr.name)
		self.assertEqual(pr.status, "Initiated")

	def test_make_payment_order_TC_ACC_158(self):
		frappe.set_user("Administrator")
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 800)
		create_account(
			account_name="_Test Account 12",
			parent_account="Bank Accounts - _TC",
			company="_Test Company",
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		bank_account = create_bank_account(
			"_Test Bank Account 1", company_account="_Test Account 12 - _TC", is_company_account=True
		)

		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 800
		pr.bank_account = bank_account.name
		pr.save()
		pr.submit()
		self.assertEqual(pr.grand_total, 800)
		self.assertEqual(pr.reference_name, pi.name)
		pr.reload()
		payment_order = make_payment_order(pr.name)
		payment_order.company_bank_account = bank_account.name
		payment_order.save()

	def test_get_open_payment_request_query_TC_ACC_159(self):
		frappe.set_user("Administrator")
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 800)
		create_account(
			account_name="_Test Account 123",
			parent_account="Bank Accounts - _TC",
			company="_Test Company",
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		bank_account = create_bank_account(
			"_Test Bank Account", company_account="_Test Account 123 - _TC", is_company_account=True
		)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 800
		pr.bank_account = bank_account.name
		pr.save()
		pr.submit()
		self.assertEqual(pr.grand_total, 800)
		self.assertEqual(pr.reference_name, pi.name)
		pr.reload()
		filters_1 = {"reference_doctype": "", "reference_name": ""}
		get_open_payment_requests_query(
			doctype="Payment Request", txt="", searchfield="name", start=0, page_len=20, filters=filters_1
		)

		filters_2 = {"reference_doctype": pr.reference_doctype, "reference_name": pr.reference_name}
		get_open_payment_requests_query(
			doctype="Payment Request",
			txt=f"{pr.name}",
			searchfield="name",
			start=0,
			page_len=20,
			filters=filters_2,
		)

		filters_3 = {
			"reference_doctype": pr.reference_doctype,
			"reference_name": pr.reference_name,
			"company": company,
			"status": ("!=", "Paid"),
			"outstanding_amount": (">", 0),
			"docstatus": 1,
		}
		get_open_payment_requests_query(
			doctype="Payment Request", txt="", searchfield="name", start=0, page_len=20, filters=filters_3
		)

	def test_get_subscription_details_TC_ACC_160(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		customer = create_customer()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		item = create_item(item_code=item_code, valuation_rate=100)
		sp_name = "_Test Plan Name"
		sp = create_subscription_plan(
			sp_name,
			plan_name="_TestPhonePay",
			subscription_based_on="Fixed Rate",
			cost=100,
			item_code=item.item_code,
		)
		subscription = create_subscription(
			trial_period_start=today(),
			trial_period_end=add_days(today(), 3),
			plans=[{"plan": sp.name, "qty": 4}],
		)
		si = frappe.get_doc(
			dict(
				doctype="Sales Invoice",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				due_date=add_days(today(), 2),
				order_type="Shopping Cart",
				subscription=subscription.name,
			)
		)
		si.append("items", {"item_code": item.item_code, "qty": 1, "rate": 200})
		si.save()
		si.submit()
		self.assertEqual(si.customer, customer)
		subscription_invoice = frappe.new_doc("Subscription Invoice")
		subscription_invoice.document_type = "Sales Invoice"
		subscription_invoice.invoice = si.name
		subscription_invoice.parent = subscription.name
		subscription_invoice.parenttype = "Subscription"
		subscription_invoice.save()
		from erpnext.accounts.doctype.payment_request.payment_request import get_subscription_details

		result = get_subscription_details(reference_doctype="Sales Invoice", reference_name=si.name)
		plan_dicts = [plan.as_dict() for plan in result]
		self.assertEqual(len(plan_dicts), 1)
		self.assertEqual(plan_dicts[0]["plan"], sp.name)

	def test_party_account_is_debit_to_for_sales_or_pos_invoice_TC_ACC_161(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		customer = create_customer()
		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		item = create_item(item_code=item_code, valuation_rate=100)
		si = frappe.get_doc(
			dict(
				doctype="Sales Invoice",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				due_date=add_days(today(), 2),
				order_type="Shopping Cart",
			)
		)
		si.append("items", {"item_code": item.item_code, "qty": 1, "rate": 200})
		si.save()
		si.submit()
		self.assertEqual(si.customer, customer)
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1, submit_doc=1, return_doc=1)
		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company=company,
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		pe = pr.create_payment_entry()
		self.assertEqual(pe.paid_from, si.debit_to)

	def test_get_payment_request_context_message_TC_ACC_162(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 800)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=1, return_doc=1)
		self.assertEqual(pr.grand_total, 800)
		self.assertEqual(pr.reference_name, pi.name)
		pr.get_message()

	def test_make_communication_entry_TC_ACC_163(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		self.assertEqual(pi.grand_total, 800)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=1, return_doc=1)
		self.assertEqual(pr.grand_total, 800)
		self.assertEqual(pr.reference_name, pi.name)
		pr.make_communication_entry()

	def test_get_existing_payment_request_amount_TC_ACC_164(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.append("items", {"item_code": item.item_code, "qty": 8, "rate": 100})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		pr_1 = make_payment_request(
			dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1
		)
		pr_1.grand_total = 400
		pr_1.save()
		pr_1.submit()

		self.assertEqual(pr_1.reference_name, pi.name)
		pr_2 = make_payment_request(
			dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=1, return_doc=1
		)
		self.assertEqual(pr_2.reference_name, pi.name)
		from erpnext.accounts.doctype.payment_request.payment_request import (
			get_existing_payment_request_amount,
		)

		get_existing_payment_request_amount(pi, ["Initiated", "Partially Paid", "Payment Ordered", "Paid"])

	def test_update_payment_requests_as_per_pe_references_TC_ACC_165(self):
		from erpnext.accounts.doctype.payment_request.payment_request import (
			update_payment_requests_as_per_pe_references,
		)

		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		customer = create_customer()

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company=company,
		)

		item = create_item(item_code=item_code, valuation_rate=100)
		si = frappe.get_doc(
			dict(
				doctype="Sales Invoice",
				customer=customer,
				set_warehouse="_Test Warehouse - _TC",
				company=company,
				currency="INR",
				due_date=add_days(today(), 2),
				order_type="Shopping Cart",
			)
		)
		si.append("items", {"item_code": item.item_code, "qty": 4, "rate": 200})
		si.save()
		si.submit()
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1, submit_doc=1, return_doc=1)
		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company=company,
			account_type="Bank",
			account_currency="INR",
			is_group=0,
		)
		pe = pr.create_payment_entry()
		with self.assertRaises(
			frappe.ValidationError,
			msg=f"The allocated amount is greater than the outstanding amount of Payment Request {pr.name}",
		):
			update_payment_requests_as_per_pe_references(references=pe.references, cancel=False)
		update_payment_requests_as_per_pe_references(references=pe.references, cancel=True)

	def test_allocate_multiple_refrences_with_split_TC_ACC_166(self):
		create_company()
		item_code = "_Test Item"
		company = "_Test Company"
		supplier = "_Test Supplier"

		create_warehouse(
			warehouse_name="_Test Warehouse - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC", "account": "Cost of Goods Sold - _TC"},
			company="_Test Company",
		)
		create_supplier(supplier_name=supplier, default_currency="INR")
		item = create_item(item_code=item_code, valuation_rate=100)
		create_payment_terms_template()
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = supplier
		pi.company = company
		pi.currency = "INR"
		pi.payment_terms_template = "Test Receivable Template"
		pi.append("items", {"item_code": item.item_code, "qty": 1, "rate": 200})
		pi.save()
		pi.submit()
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.company, company)
		self.assertEqual(pi.items[0].item_code, item.item_code)
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 100
		pr.outstanding_amount = 60
		pr.save()
		pr.submit()
		self.assertEqual(pr.reference_name, pi.name)
		pe = pr.create_payment_entry(submit=False)
		pe.save()
		self.assertEqual(pe.references[0].allocated_amount, 100)
		self.assertEqual(pe.references[0].outstanding_amount, 200)
		self.assertEqual(pe.references[1].allocated_amount, 69.49)
		self.assertEqual(pe.references[1].outstanding_amount, 200)
		self.assertEqual(pe.references[2].allocated_amount, 30.51)
		self.assertEqual(pe.references[2].outstanding_amount, 200)

	def test_consider_journal_entry_and_return_invoice(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		si = create_sales_invoice(currency="INR", qty=5, rate=500)

		je = make_journal_entry("_Test Cash - _TC", "Debtors - _TC", 500, save=False)
		je.accounts[1].party_type = "Customer"
		je.accounts[1].party = si.customer
		je.accounts[1].reference_type = "Sales Invoice"
		je.accounts[1].reference_name = si.name
		je.accounts[1].credit_in_account_currency = 500
		je.submit()

		pe = get_payment_entry("Sales Invoice", si.name)
		pe.paid_amount = 500
		pe.references[0].allocated_amount = 500
		pe.save()
		pe.submit()

		cr_note = create_sales_invoice(qty=-1, rate=500, is_return=1, return_against=si.name, do_not_save=1)
		cr_note.update_outstanding_for_self = 0
		cr_note.save()
		cr_note.submit()

		si.load_from_db()
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1)
		self.assertEqual(pr.grand_total, si.outstanding_amount)

	def test_set_payment_request_url_TC_ACC_359(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			make_test_item,
		)
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company("_Test Company")
		get_or_create_fiscal_year("_Test Company")
		customer = create_customer("_Test Customer")
		create_warehouse("_Test Warehouse")
		item = make_test_item("_Test Item")
		si = create_sales_invoice(
			customer=customer,
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			currency="INR",
			warehouse="_Test Warehouse - _TC",
		)
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1, submit_doc=0)
		pr_doc = frappe.get_doc("Payment Request", pr.name)
		rz = frappe.get_doc(
			{
				"doctype": "Razorpay Settings",
				"api_key": "test_api_key",
				"api_secret": "test_api_secret",
				"redirect_to": "http://localhost:8000",
			}
		)
		rz.flags.ignore_validate = True
		rz.save(ignore_permissions=True)
		pg = create_payment_gateway_account(
			pg_name="Test Payment Gateway", payment_channel="Email", is_default=True
		)
		pr_doc.payment_gateway_account = pg.name
		pr_doc.payment_gateway = "Test Payment Gateway"
		pr_doc.save(ignore_permissions=True)
		pg_doc = frappe.get_doc("Payment Gateway", "Test Payment Gateway")
		pg_doc.gateway_settings = rz.doctype
		pg_doc.gateway_controller = rz.name
		pg_doc.save(ignore_permissions=True)
		pr_doc.set_payment_request_url()
		self.assertTrue(pr_doc.payment_url)

	def test_request_phone_payment_TC_ACC_360(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		rz = None
		create_company("_Test Company")
		get_or_create_fiscal_year("_Test Company")
		customer = create_customer("_Test Customer")
		create_warehouse("_Test Warehouse")
		item = make_test_item("_Test Item")

		si = create_sales_invoice(
			customer=customer,
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=500,
			currency="KES",
			warehouse="_Test Warehouse - _TC",
		)

		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1, submit_doc=0)
		pr_doc = frappe.get_doc("Payment Request", pr.name)

		if not frappe.db.exists("Mpesa Settings", {"payment_gateway_name": "Test Mpesa Gateway New"}):
			rz = frappe.get_doc(
				{
					"doctype": "Mpesa Settings",
					"payment_gateway_name": "Test Mpesa Gateway New",
					"consumer_key": "test_consumer_key",
					"consumer_secret": "test_consumer_secret",
					"business_shortcode": "test_business_shortcode",
					"online_passkey": "test_online_passkey",
					"till_number": "1234567890",
					"transaction_limit": 15000,
				}
			)
			rz.flags.ignore_validate = True
			rz.insert(ignore_permissions=True)
		else:
			rz = frappe.get_doc("Mpesa Settings", "Test Mpesa Gateway New")
		m_pg = create_payment_gateway_account(
			pg_name="Mpesa-" + rz.payment_gateway_name, payment_channel="Phone", is_default=True
		)
		payment_account = frappe.get_value(
			"Payment Gateway Account",
			{"payment_gateway": "Mpesa-" + rz.payment_gateway_name},
			["name", "payment_account"],
			as_dict=1,
		)
		if payment_account and payment_account.payment_account != "Cash - _TC":
			frappe.db.set_value(
				"Payment Gateway Account", payment_account.name, "payment_account", "Cash - _TC"
			)
		pg = create_payment_gateway_account(
			pg_name="Test Phone Gateway", payment_channel="Phone", is_default=True
		)
		pr_doc.payment_gateway_account = pg.name
		pr_doc.payment_gateway = "Test Phone Gateway"
		pr_doc.phone_number = "9999999999"
		pr_doc.save(ignore_permissions=True)

		pg_doc = frappe.get_doc("Payment Gateway", "Test Phone Gateway")
		pg_doc.gateway_settings = rz.doctype
		pg_doc.gateway_controller = rz.name
		pg_doc.save(ignore_permissions=True)

		pr_doc.request_phone_payment()

		ir = frappe.get_all(
			"Integration Request",
			filters={"reference_doctype": "Payment Request", "reference_docname": pr_doc.name},
			limit=1,
		)
		self.assertTrue(ir)
		if ir:
			frappe.db.set_value("Integration Request", ir[0], "status", "Completed")
		request_amount = pr_doc.get_request_amount()
		self.assertEqual(request_amount, pr_doc.grand_total)
		frappe.delete_doc("Payment Request", pr_doc.name, force=True)
		frappe.delete_doc("Payment Gateway Account", pg.name, force=True)
		frappe.delete_doc("Payment Gateway", "Test Phone Gateway", force=True)
		frappe.delete_doc("Mpesa Settings", "Test Mpesa Gateway New", force=True)
		frappe.db.rollback()

	def test_cancel_old_payment_requests_TC_ACC_361(self):
		import json

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_request.payment_request import (
			cancel_old_payment_requests,
			make_payment_request,
		)
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company("_Test Company")
		get_or_create_fiscal_year("_Test Company")
		customer = create_customer("_Test Customer")
		create_warehouse("_Test Warehouse")
		item = make_test_item("_Test Item")

		si = create_sales_invoice(
			customer=customer,
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=200,
			currency="INR",
			warehouse="_Test Warehouse - _TC",
		)

		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1, submit_doc=1)
		pr_doc = frappe.get_doc("Payment Request", pr.name)
		pr_doc.status = "Requested"
		pr_doc.save(ignore_permissions=True)

		ireq = frappe.get_doc(
			{
				"doctype": "Integration Request",
				"reference_doctype": "Payment Request",
				"reference_docname": pr_doc.name,
				"status": "Queued",
				"data": json.dumps({"request_amount": pr_doc.grand_total}),
			}
		)
		ireq.insert(ignore_permissions=True)

		cancel_old_payment_requests("Sales Invoice", si.name)

		pr_doc.reload()
		ireq.reload()

		self.assertEqual(pr_doc.docstatus, 2)

		self.assertEqual(ireq.status, "Cancelled")

	def test_get_irequest_status_TC_ACC_362(self):
		import json

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_request.payment_request import (
			get_irequest_status,
			make_payment_request,
		)
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_company("_Test Company")
		get_or_create_fiscal_year("_Test Company")
		customer = create_customer("_Test Customer")
		create_warehouse("_Test Warehouse")
		item = make_test_item("_Test Item")

		si = create_sales_invoice(
			customer=customer,
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=300,
			currency="INR",
			warehouse="_Test Warehouse - _TC",
		)

		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1, submit_doc=1)
		pr_doc = frappe.get_doc("Payment Request", pr.name)

		result = get_irequest_status([pr_doc.name])
		self.assertEqual(result, [])

		ireq = frappe.get_doc(
			{
				"doctype": "Integration Request",
				"reference_doctype": "Payment Request",
				"reference_docname": pr_doc.name,
				"status": "Completed",
				"data": json.dumps({"request_amount": pr_doc.grand_total}),
			}
		)
		ireq.insert(ignore_permissions=True)

		result = get_irequest_status([pr_doc.name])
		self.assertTrue(result)
		self.assertEqual(result[0]["name"], ireq.name)


def test_partial_paid_invoice_with_submitted_payment_entry(self):
	pi = make_purchase_invoice(currency="INR", qty=1, rate=5000)
	pi.save()
	pi.submit()
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "PURINV0001"
	pe.reference_date = frappe.utils.nowdate()
	pe.paid_amount = 2500
	pe.references[0].allocated_amount = 2500
	pe.save()
	pe.submit()
	pe.cancel()
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
	pe.reference_no = "PURINV0002"
	pe.reference_date = frappe.utils.nowdate()
	pe.paid_amount = 2500
	pe.references[0].allocated_amount = 2500
	pe.save()
	pe.submit()
	pi.load_from_db()
	pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1)
	self.assertEqual(pr.grand_total, pi.outstanding_amount)


def create_payment_gateway_account(pg_name, payment_channel=None, is_default=False):
	default_channel = "Email"
	if not frappe.db.exists("Payment Gateway", pg_name):
		frappe.get_doc(dict(doctype="Payment Gateway", gateway=pg_name)).insert()
	if not frappe.db.exists("Payment Gateway Account", {"payment_gateway": pg_name}):
		pg = frappe.get_doc(
			dict(
				doctype="Payment Gateway Account",
				payment_gateway=pg_name,
				payment_account="Cash - _TC",
				payment_channel=payment_channel or default_channel,
				is_default=is_default,
			)
		).insert()
	else:
		all_pg = frappe.get_all(
			"Payment Gateway Account", filters={"payment_gateway": pg_name}, fields=["name"]
		)
		pg = frappe.get_doc("Payment Gateway Account", all_pg[0].get("name"))
	return pg


def create_subscription_plan(sp_name, **kwargs):
	if not frappe.db.exists("Subscription Plan", sp_name):
		sp = frappe.get_doc(
			dict(
				doctype="Subscription Plan",
				plan_name=kwargs.get("plan_name"),
				currency=kwargs.get("currency") or "INR",
				item=kwargs.get("item_code"),
				price_determination=kwargs.get("subscription_based_on"),
				cost=kwargs.get("cost"),
				payment_gateway=kwargs.get("payment_gateway"),
				payment_channel=kwargs.get("payment_channel"),
			)
		).insert()
	else:
		sp = frappe.get_doc("Subscription Plan", sp_name)
	return sp


def create_loyalty_program(loyalty_program_name, company=None):
	if not frappe.db.exists("Loyalty Program", loyalty_program_name):
		lp = frappe.get_doc(
			dict(
				doctype="Loyalty Program",
				loyalty_program_name=loyalty_program_name,
				from_date=today(),
				to_date=add_days(today(), 10),
				company=company or "_Test Company",
				conversion_factor=1,
			)
		)
		lp.append("collection_rules", {"tier_name": "first tier", "collection_factor": 2})
		lp.insert(ignore_permissions=True)
	else:
		lp = frappe.get_doc("Loyalty Program", loyalty_program_name)
	return lp


def create_mode_of_payment(mode_of_payment, type, **kwargs):
	existing_mop = frappe.db.get_value(
		"Mode of Payment", {"mode_of_payment": mode_of_payment}, ["name", "enabled"], as_dict=True
	)

	if existing_mop:
		if not existing_mop.enabled:
			frappe.db.set_value("Mode of Payment", existing_mop.name, "enabled", 1)
		mop = frappe.get_doc("Mode of Payment", existing_mop.name)
	else:
		mop = frappe.get_doc(dict(doctype="Mode of Payment", mode_of_payment=mode_of_payment, type=type))
		mop.append(
			"accounts", dict(company=kwargs.get("company"), default_account=kwargs.get("default_account"))
		)
		mop.insert(ignore_permissions=True)

	return mop


def create_price_list():
	if not frappe.db.exists("Price List", "_Test Price List"):
		price_list = frappe.get_doc(
			dict(doctype="Price List", price_list_name="_Test Price List", currency="INR", selling=1)
		)
		price_list.insert()
	else:
		price_list = frappe.get_doc("Price List", "_Test Price List")
	if not frappe.db.exists("Item Price", {"item_code": "_Test Item", "price_list": price_list.name}):
		item_price = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": "_Test Item",
				"price_list": price_list.name,
				"price_list_rate": "450",
			}
		)
		item_price.insert()
	else:
		item_price = frappe.get_doc("Item Price", {"item_code": "_Test Item", "price_list": price_list.name})

	return item_price


def create_bank_account(account_name, company_account, is_company_account=False):
	create_company()
	bank_account = frappe._dict()
	if not frappe.db.exists("Bank", "_Test Bank"):
		bank = frappe.get_doc(dict(doctype="Bank", bank_name="_Test Bank")).insert(ignore_permissions=True)
	else:
		bank = frappe.get_doc("Bank", "_Test Bank")
	full_name = f"{account_name} - {bank.name}"
	if not frappe.db.exists("Bank Account", full_name):
		bank_account = frappe.get_doc(
			dict(
				doctype="Bank Account",
				account_name=account_name,
				bank=bank.name,
				is_company_account=is_company_account,
			)
		)
		if is_company_account == True:
			bank_account.account = company_account
		bank_account.insert(ignore_permissions=True)
	else:
		bank_account = frappe.get_doc("Bank Account", full_name)
	return bank_account
