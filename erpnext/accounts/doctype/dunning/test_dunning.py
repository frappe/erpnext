# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

import frappe
from frappe.model import mapper
from frappe.utils import add_days, nowdate, today

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.mapper import (
	create_dunning as create_dunning_from_sales_invoice,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	create_sales_invoice,
	create_sales_invoice_against_cost_center,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestDunning(ERPNextTestSuite):
	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1}
	)
	def test_document_api_defaults_converted_fee_and_preserves_overrides(self):
		from frappe.client import insert

		create_dunning_type("API Fee Notice", 100, 0, 0)
		invoice = create_sales_invoice(
			posting_date=add_days(today(), -15),
			currency="USD",
			conversion_rate=80,
			rate=100,
			debit_to="Debtors - _TC",
		)
		for fee, expected in ((None, 1.25), (0, 0), (7, 7)):
			with self.subTest(fee=fee):
				payload = create_dunning_from_sales_invoice(invoice.name).as_dict()
				payload.dunning_type = "API Fee Notice - _TC"
				if fee is None:
					payload.pop("dunning_fee")
				else:
					payload.dunning_fee = fee
				dunning = frappe.get_doc("Dunning", insert(payload)["name"])
				self.assertEqual(dunning.dunning_fee, expected)
				dunning.conversion_rate = 100
				dunning.save()
				self.assertEqual(dunning.dunning_fee, 1 if fee is None else fee)
				self.assertEqual(dunning.base_dunning_amount, dunning.dunning_amount * 100)

	def test_missing_fee_requires_positive_conversion_rate(self):
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")
		for rate in (0, -1):
			with self.subTest(rate=rate):
				dunning.reload()
				dunning.dunning_fee = None
				dunning.conversion_rate = rate
				with self.assertRaisesRegex(frappe.ValidationError, "Conversion Rate must be greater"):
					dunning.save()

	def test_unallocated_payments_reduce_oldest_installments(self):
		create_payment_terms_template_for_dunning()
		frappe.db.set_value(
			"Payment Terms Template", "_Test 50-50 for Dunning", "allocate_payment_based_on_payment_terms", 0
		)
		for overdue_days, paid_amount, expected in (
			(15, 20, [(0, 30), (1, 50)]),
			(15, 60, [(1, 40)]),
			(6, 20, [(0, 30)]),
			(6, 50, []),
		):
			with self.subTest(overdue_days=overdue_days, paid_amount=paid_amount):
				invoice = create_sales_invoice_against_cost_center(
					posting_date=add_days(today(), -overdue_days), qty=1, rate=100, do_not_submit=True
				)
				invoice.payment_terms_template = "_Test 50-50 for Dunning"
				invoice.submit()
				draft = create_dunning_from_sales_invoice(invoice.name)
				draft.save()
				payment = get_payment_entry("Sales Invoice", invoice.name)
				payment.paid_amount = payment.received_amount = paid_amount
				payment.references[0].allocated_amount = paid_amount
				payment.reference_no, payment.reference_date = "1", today()
				payment.insert().submit()
				invoice.reload()
				self.assertEqual([row.outstanding for row in invoice.payment_schedule], [50, 50])
				with self.assertRaisesRegex(frappe.ValidationError, "cannot exceed the unpaid"):
					draft.save()
				draft.reload()
				with self.assertRaisesRegex(frappe.ValidationError, "cannot exceed the unpaid"):
					draft.submit()

				if not expected:
					with self.assertRaisesRegex(frappe.ValidationError, "There are no overdue payments"):
						create_dunning_from_sales_invoice(invoice.name)
					continue

				dunning = create_dunning_from_sales_invoice(invoice.name)
				dunning.rate_of_interest = 36.5
				dunning.save()
				self.assertEqual(
					[(row.payment_schedule, row.outstanding) for row in dunning.overdue_payments],
					[(invoice.payment_schedule[idx].name, amount) for idx, amount in expected],
				)
				for row in dunning.overdue_payments:
					self.assertAlmostEqual(row.interest, row.outstanding * int(row.overdue_days) / 1000, 2)

	def test_copied_payment_schedule_fields_cannot_be_changed(self):
		dunning = create_dunning(overdue_days=15)
		row = dunning.overdue_payments[0]
		for field, value in (
			("payment_term", "_Test Payment Term"),
			("mode_of_payment", "Cash"),
			("payment_amount", row.payment_amount + 1),
			("invoice_portion", row.invoice_portion + 1),
		):
			with self.subTest(field=field):
				original = row.get(field)
				row.set(field, value)
				with self.assertRaisesRegex(frappe.ValidationError, "must match the Payment Schedule"):
					dunning.validate_overdue_payment_references()
				row.set(field, original)
		dunning.validate_overdue_payment_references()

	def test_dunning_without_fees(self):
		dunning = create_dunning(overdue_days=20)

		self.assertEqual(round(dunning.total_outstanding, 2), 100.00)
		self.assertEqual(round(dunning.total_interest, 2), 0.00)
		self.assertEqual(round(dunning.dunning_fee, 2), 0.00)
		self.assertEqual(round(dunning.dunning_amount, 2), 0.00)
		self.assertEqual(round(dunning.grand_total, 2), 100.00)

	def test_dunning_with_fees_and_interest(self):
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")

		self.assertEqual(round(dunning.total_outstanding, 2), 100.00)
		self.assertEqual(round(dunning.total_interest, 2), 0.41)
		self.assertEqual(round(dunning.dunning_fee, 2), 10.00)
		self.assertEqual(round(dunning.dunning_amount, 2), 10.41)
		self.assertEqual(round(dunning.grand_total, 2), 110.41)

	def test_dunning_with_payment_entry(self):
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")
		dunning.submit()
		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.insert()
		pe.submit()

		for overdue_payment in dunning.overdue_payments:
			outstanding_amount = frappe.get_value(
				"Sales Invoice", overdue_payment.sales_invoice, "outstanding_amount"
			)
			self.assertEqual(outstanding_amount, 0)

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")

	def test_dunning_not_resolved_by_payment_of_invoiced_sum_only(self):
		"""
		Regression for #58220: paying the invoice without the interest and fee must not
		resolve the dunning, the interest is still owed and has to stay claimable.
		"""
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")
		dunning.submit()
		sales_invoice = dunning.overdue_payments[0].sales_invoice

		pe = get_payment_entry("Sales Invoice", sales_invoice)
		pe.reference_no, pe.reference_date = "4", nowdate()
		pe.insert()
		pe.submit()

		self.assertEqual(frappe.get_value("Sales Invoice", sales_invoice, "outstanding_amount"), 0)

		dunning.reload()
		self.assertEqual(dunning.status, "Unresolved")
		self.assertEqual(round(dunning.get_unpaid_dunning_amount(), 2), 10.41)

		# the interest and fee can still be collected on their own
		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no, pe.reference_date = "5", nowdate()
		self.assertEqual(pe.references, [])
		self.assertEqual(round(pe.paid_amount, 2), 10.41)
		pe.insert()
		pe.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")
		self.assertEqual(dunning.get_unpaid_dunning_amount(), 0)

		# cancelling the interest payment makes the dunning claimable again
		pe.cancel()
		dunning.reload()
		self.assertEqual(dunning.status, "Unresolved")
		self.assertEqual(round(dunning.get_unpaid_dunning_amount(), 2), 10.41)

	def test_dunning_can_be_cancelled_after_its_interest_was_paid(self):
		"""
		The payment collecting the interest links back to the dunning, which must not stand in
		the way of cancelling it.
		"""
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")
		dunning.submit()

		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no, pe.reference_date = "6", nowdate()
		pe.insert()
		pe.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")

		dunning.cancel()
		self.assertEqual(dunning.docstatus, 2)

	def test_waived_interest_keeps_a_manually_resolved_dunning_resolved(self):
		"""
		Resolving a dunning by hand waives its interest, so a later payment of the invoice
		must not reopen it.
		"""
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")
		dunning.submit()
		sales_invoice = dunning.overdue_payments[0].sales_invoice

		# what the "Resolve" button does
		dunning.reload()
		dunning.status = "Resolved"
		dunning.save()

		pe = get_payment_entry("Sales Invoice", sales_invoice)
		pe.reference_no, pe.reference_date = "7", nowdate()
		pe.insert()
		pe.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")
		self.assertEqual(round(dunning.get_unpaid_dunning_amount(), 2), 10.41)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1}
	)
	def test_unpaid_dunning_amount_is_tracked_in_company_currency(self):
		"""
		The interest and fee are collected as a Payment Entry deduction, a company currency
		field, so what is left to collect has to be measured in the same currency.
		"""
		si = create_sales_invoice(
			posting_date=add_days(today(), -15),
			currency="USD",
			conversion_rate=50,
			rate=100,
			debit_to="Debtors - _TC",
		)

		dunning = create_dunning_from_sales_invoice(si.name)
		dunning_type = frappe.get_doc("Dunning Type", "Second Notice - _TC")
		dunning.dunning_type = dunning_type.name
		dunning.rate_of_interest = dunning_type.rate_of_interest
		dunning.dunning_fee = dunning_type.dunning_fee
		dunning.income_account = dunning_type.income_account
		dunning.cost_center = dunning_type.cost_center
		dunning.save()

		self.assertEqual(dunning.currency, "USD")
		self.assertEqual(dunning.conversion_rate, 50)
		self.assertEqual(round(dunning.dunning_amount, 2), 10.41)
		self.assertEqual(round(dunning.base_dunning_amount, 2), 520.55)

		# nothing collected yet, in either currency
		self.assertEqual(round(dunning.get_unpaid_base_dunning_amount(), 2), 520.55)
		self.assertEqual(round(dunning.get_unpaid_dunning_amount(), 2), 10.41)

		# the deduction booking the interest is in company currency
		dunning.submit()
		pe = get_payment_entry("Dunning", dunning.name)
		self.assertEqual(round(pe.deductions[0].amount, 2), -520.55)

	def test_fetch_overdue_payments(self):
		"""
		Create SI with overdue payment. Check if overdue payment is fetched in Dunning.
		"""
		si1 = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -1 * 6),
			qty=1,
			rate=100,
		)

		si2 = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -1 * 6),
			qty=1,
			rate=300,
		)

		dunning = create_dunning_from_sales_invoice(si1.name)
		dunning.overdue_payments = []

		method = "erpnext.accounts.doctype.sales_invoice.mapper.create_dunning"
		updated_dunning = mapper.map_docs(method, json.dumps([si1.name, si2.name]), dunning)

		self.assertEqual(len(updated_dunning.overdue_payments), 2)

		self.assertEqual(updated_dunning.overdue_payments[0].sales_invoice, si1.name)
		self.assertEqual(updated_dunning.overdue_payments[0].outstanding, si1.outstanding_amount)

		self.assertEqual(updated_dunning.overdue_payments[1].sales_invoice, si2.name)
		self.assertEqual(updated_dunning.overdue_payments[1].outstanding, si2.outstanding_amount)

	def test_fetch_overdue_payments_with_dialog_args(self):
		create_payment_terms_template_for_dunning()
		invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -15), qty=1, rate=100, do_not_submit=True
		)
		invoice.payment_terms_template = "_Test 50-50 for Dunning"
		invoice.submit()
		method = "erpnext.accounts.doctype.sales_invoice.mapper.create_dunning"

		for selected in ([], [invoice.payment_schedule[1].name]):
			with self.subTest(selected=selected):
				dunning = mapper.map_docs(
					method,
					[invoice.name],
					{"doctype": "Dunning", "company": invoice.company},
					args={
						"customer": invoice.customer,
						"allow_child_item_selection": int(bool(selected)),
						"filtered_children": selected,
					},
				)
				self.assertEqual(
					[row.payment_schedule for row in dunning.overdue_payments],
					selected or [row.name for row in invoice.payment_schedule],
				)
				self.assertEqual(dunning.total_outstanding, 50 if selected else 100)

		with self.set_user("Guest"):
			with self.assertRaises(frappe.PermissionError):
				mapper.map_docs(
					method,
					[invoice.name],
					{"doctype": "Dunning", "company": invoice.company},
					args={"customer": invoice.customer, "filtered_children": []},
				)

	def test_fetch_overdue_payments_with_positional_ignore_permissions(self):
		invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -15), qty=1, rate=100
		)

		for ignore_permissions in (False, True):
			with self.subTest(ignore_permissions=ignore_permissions):
				dunning = create_dunning_from_sales_invoice(invoice.name, None, ignore_permissions)
				self.assertEqual(dunning.overdue_payments[0].sales_invoice, invoice.name)
				self.assertEqual(dunning.total_outstanding, 100)

		with self.set_user("Guest"):
			# Ignoring mapper permissions does not bypass Customer permissions during validation.
			for ignore_permissions in (False, True):
				with self.subTest(ignore_permissions=ignore_permissions):
					with self.assertRaises(frappe.PermissionError):
						create_dunning_from_sales_invoice(invoice.name, None, ignore_permissions)

	def test_dunning_and_payment_against_partially_due_invoice(self):
		"""
		Create SI with first installment overdue. Check impact of Dunning and Payment Entry.
		"""
		create_payment_terms_template_for_dunning()
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -1 * 6),
			qty=1,
			rate=100,
			do_not_submit=True,
		)
		sales_invoice.payment_terms_template = "_Test 50-50 for Dunning"
		sales_invoice.submit()
		dunning = create_dunning_from_sales_invoice(sales_invoice.name)

		self.assertEqual(len(dunning.overdue_payments), 1)
		self.assertEqual(dunning.overdue_payments[0].payment_term, "_Test Payment Term 1 for Dunning")

		dunning.submit()
		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no, pe.reference_date = "2", nowdate()
		pe.insert()
		pe.submit()
		sales_invoice.load_from_db()
		dunning.load_from_db()

		self.assertEqual(sales_invoice.status, "Partly Paid")
		self.assertEqual(sales_invoice.payment_schedule[0].outstanding, 0)
		self.assertEqual(dunning.status, "Resolved")

		# Test impact on cancellation of PE
		pe.cancel()
		sales_invoice.reload()
		dunning.reload()

		self.assertEqual(sales_invoice.status, "Overdue")
		self.assertEqual(dunning.status, "Unresolved")

	def test_payment_against_invoice_with_multiple_overdue_installments_in_dunning(self):
		"""
		When an invoice has more than one overdue installment, its Dunning holds one
		Overdue Payment row per installment. Submitting a Payment Entry for the invoice
		must resolve the Dunning without raising a TimestampMismatchError caused by the
		same Dunning being loaded and saved more than once.
		"""
		create_payment_terms_template_for_dunning()
		# Post far enough in the past that BOTH installments (5 and 10 credit days) are overdue.
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -15),
			qty=1,
			rate=100,
			do_not_submit=True,
		)
		sales_invoice.payment_terms_template = "_Test 50-50 for Dunning"
		sales_invoice.submit()

		dunning = create_dunning_from_sales_invoice(sales_invoice.name)
		# Two overdue installments -> two overdue payment rows for the same invoice.
		self.assertEqual(len(dunning.overdue_payments), 2)
		dunning.submit()
		self.assertEqual(dunning.status, "Unresolved")

		# Pay the invoice in full. This previously raised TimestampMismatchError on the Dunning.
		pe = get_payment_entry("Sales Invoice", sales_invoice.name)
		pe.reference_no, pe.reference_date = "3", nowdate()
		pe.insert()
		pe.submit()

		sales_invoice.reload()
		dunning.reload()
		self.assertEqual(sales_invoice.outstanding_amount, 0)
		self.assertEqual(dunning.status, "Resolved")

	def test_dunning_resolution_from_credit_note(self):
		"""
		Test that dunning is resolved when a credit note is issued against the original invoice.
		"""
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -10), qty=1, rate=100
		)
		dunning = create_dunning_from_sales_invoice(sales_invoice.name)
		dunning.submit()

		self.assertEqual(dunning.status, "Unresolved")

		credit_note = frappe.copy_doc(sales_invoice)
		credit_note.is_return = 1
		credit_note.return_against = sales_invoice.name
		credit_note.update_outstanding_for_self = 0

		for item in credit_note.items:
			item.qty = -item.qty

		credit_note.save()
		credit_note.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")

		credit_note.cancel()
		dunning.reload()
		self.assertEqual(dunning.status, "Unresolved")

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1}
	)
	def test_dunning_outstanding_uses_transaction_currency(self):
		"""
		Regression for #56006: dunning outstanding must be in the invoice transaction
		currency, not in the party account currency.

		A USD invoice posted against an INR receivable account stores
		outstanding_amount in INR (party account currency).  The overdue payment
		row on the resulting Dunning must carry the USD amount, not the INR amount.
		"""
		si = create_sales_invoice(
			posting_date=add_days(today(), -10),
			currency="USD",
			conversion_rate=50,
			rate=100,
			debit_to="Debtors - _TC",
		)

		# Sanity-check the invoice state before creating the dunning
		self.assertEqual(si.currency, "USD")
		self.assertEqual(si.outstanding_amount, 5000.0)  # INR (party account currency)
		self.assertEqual(si.payment_schedule[0].outstanding, 100.0)  # USD (transaction currency)

		dunning = create_dunning_from_sales_invoice(si.name)

		self.assertEqual(len(dunning.overdue_payments), 1)
		# Must reflect 100 USD, not 5000 INR mislabelled as USD
		self.assertEqual(dunning.overdue_payments[0].outstanding, 100.0)

	def test_dunning_not_affected_by_standalone_credit_note(self):
		"""
		Test that dunning is NOT resolved when a credit note has update_outstanding_for_self checked.
		"""
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -10), qty=1, rate=100
		)
		dunning = create_dunning_from_sales_invoice(sales_invoice.name)
		dunning.submit()

		self.assertEqual(dunning.status, "Unresolved")

		credit_note = frappe.copy_doc(sales_invoice)
		credit_note.is_return = 1
		credit_note.return_against = sales_invoice.name
		credit_note.update_outstanding_for_self = 1

		for item in credit_note.items:
			item.qty = -item.qty

		credit_note.save()

		credit_note = frappe.get_doc("Sales Invoice", credit_note.name)
		credit_note.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Unresolved")


def create_dunning(overdue_days, dunning_type_name=None):
	posting_date = add_days(today(), -1 * overdue_days)
	sales_invoice = create_sales_invoice_against_cost_center(posting_date=posting_date, qty=1, rate=100)
	dunning = create_dunning_from_sales_invoice(sales_invoice.name)

	if dunning_type_name:
		dunning_type = frappe.get_doc("Dunning Type", dunning_type_name)
		dunning.dunning_type = dunning_type.name
		dunning.rate_of_interest = dunning_type.rate_of_interest
		dunning.dunning_fee = dunning_type.dunning_fee
		dunning.income_account = dunning_type.income_account
		dunning.cost_center = dunning_type.cost_center

	return dunning.save()


def create_dunning_type(title, fee, interest, is_default):
	company = "_Test Company"
	if frappe.db.exists("Dunning Type", f"{title} - _TC"):
		return

	dunning_type = frappe.new_doc("Dunning Type")
	dunning_type.dunning_type = title
	dunning_type.company = company
	dunning_type.is_default = is_default
	dunning_type.dunning_fee = fee
	dunning_type.rate_of_interest = interest
	dunning_type.income_account = get_income_account(company)
	dunning_type.cost_center = get_default_cost_center(company)
	dunning_type.append(
		"dunning_letter_text",
		{
			"language": "en",
			"body_text": "We have still not received payment for our invoice",
			"closing_text": "We kindly request that you pay the outstanding amount immediately, including interest and late fees.",
		},
	)
	dunning_type.insert()


def get_income_account(company):
	return (
		frappe.get_value("Company", company, "default_income_account")
		or frappe.get_all(
			"Account",
			filters={"is_group": 0, "company": company},
			or_filters={
				"report_type": "Profit and Loss",
				"account_type": ("in", ("Income Account", "Temporary")),
			},
			limit=1,
			pluck="name",
		)[0]
	)


def create_payment_terms_template_for_dunning():
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_term

	create_payment_term("_Test Payment Term 1 for Dunning")
	create_payment_term("_Test Payment Term 2 for Dunning")

	if not frappe.db.exists("Payment Terms Template", "_Test 50-50 for Dunning"):
		frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test 50-50 for Dunning",
				"allocate_payment_based_on_payment_terms": 1,
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "_Test Payment Term 1 for Dunning",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 5,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "_Test Payment Term 2 for Dunning",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 10,
					},
				],
			}
		).insert()
