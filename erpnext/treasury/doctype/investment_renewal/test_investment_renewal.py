# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import frappe
from frappe.utils import add_days, date_diff, getdate, nowdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	create_financial_institution,
	create_investment_type,
)
from erpnext.treasury.doctype.investment_renewal.investment_renewal import make_new_investment
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	make_submitted_investment,
	make_transaction,
)


class TestInvestmentRenewal(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")

		self.investment = make_original_investment()

	def test_renewal_cannot_reinvest_more_than_was_paid_out(self):
		cancelled_investment = make_submitted_investment()
		cancelled_investment.cancel()
		renewal = make_renewal(cancelled_investment.name, principal_renewed=1000)
		self.assertRaises(frappe.ValidationError, renewal.insert)

		make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()
		for renewed in (
			{"principal_renewed": 100001},
			{"principal_renewed": 100000, "interest_renewed": 500},  # no interest was received
		):
			with self.subTest(renewed):
				renewal = make_renewal(self.investment.name, **renewed).insert()
				self.assertRaises(frappe.ValidationError, renewal.submit)

		# the same proceeds cannot be renewed twice
		make_renewal(self.investment.name, principal_renewed=60000).insert().submit()
		renewal = make_renewal(self.investment.name, principal_renewed=50000).insert()
		self.assertRaises(frappe.ValidationError, renewal.submit)

	def test_renewal_type_is_set_from_instrument(self):
		renewal = make_renewal(self.investment.name, principal_renewed=1000).insert()

		self.assertEqual(renewal.renewal_type, "Auto Renewal")

	def test_cannot_cancel_payment_a_renewal_reinvested(self):
		maturity = make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()
		make_renewal(self.investment.name, principal_renewed=60000).insert().submit()

		self.assertRaises(frappe.ValidationError, maturity.cancel)

	def test_submitted_renewal_makes_one_draft_new_investment(self):
		make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()
		renewal = make_renewal(self.investment.name, principal_renewed=100000).insert()
		# not before the renewal is submitted
		self.assertRaises(frappe.ValidationError, make_new_investment, renewal.name)

		renewal.submit()
		new_investment = frappe.get_doc("Investment", renewal.new_investment)

		self.assertEqual(new_investment.docstatus, 0)
		self.assertEqual(new_investment.investment_renewal, renewal.name)
		self.assertEqual(
			frappe.db.get_value("Investment Renewal", renewal.name, "new_investment"), new_investment.name
		)
		# same tenure, renewed amount
		self.assertEqual(getdate(new_investment.purchase_date), getdate(renewal.renewal_date))
		self.assertEqual(new_investment.approved_amount, 100000)
		self.assertEqual(new_investment.principal_amount, 100000)
		self.assertEqual(
			date_diff(new_investment.maturity_date, new_investment.purchase_date),
			date_diff(self.investment.maturity_date, self.investment.purchase_date),
		)
		# only one
		self.assertRaises(frappe.ValidationError, make_new_investment, renewal.name)

	def test_renewal_cancels_only_when_new_investment_is_gone_or_cancelled(self):
		renewal = make_submitted_renewal(self.investment.name)

		renewal.reload()
		self.assertRaises(frappe.ValidationError, renewal.cancel)
		self.assertTrue(frappe.db.exists("Investment", renewal.new_investment))

		# deleting the draft frees the renewal to make a new one
		frappe.delete_doc("Investment", renewal.new_investment)
		self.assertFalse(frappe.db.get_value("Investment Renewal", renewal.name, "new_investment"))
		new_investment = make_new_investment(renewal.name).insert().submit()

		renewal.reload()
		self.assertRaises(frappe.ValidationError, renewal.cancel)

		new_investment.cancel()
		renewal.reload()
		renewal.cancel()
		self.assertEqual(frappe.db.get_value("Investment", new_investment.name, "docstatus"), 2)

	def test_amended_renewal_creates_new_draft(self):
		# the draft was deleted, so the amended renewal starts a fresh one
		renewal = make_submitted_renewal(self.investment.name)
		frappe.delete_doc("Investment", renewal.new_investment)
		renewal.reload()
		renewal.cancel()

		amended = amend_renewal(renewal)

		self.assertEqual(
			frappe.db.get_value("Investment", amended.new_investment, "investment_renewal"), amended.name
		)
		self.assertEqual(frappe.db.get_value("Investment", amended.new_investment, "docstatus"), 0)
		self.assertFalse(frappe.db.get_value("Investment", amended.new_investment, "amended_from"))

		# the new investment was cancelled, so the amended renewal's draft amends it
		renewal = make_submitted_renewal(make_original_investment().name)
		old_investment = frappe.get_doc("Investment", renewal.new_investment)
		old_investment.submit()
		old_investment.cancel()
		renewal.reload()
		renewal.cancel()

		amended = amend_renewal(renewal)
		new_investment = frappe.get_doc("Investment", amended.new_investment)

		self.assertEqual(new_investment.docstatus, 0)
		self.assertEqual(new_investment.amended_from, old_investment.name)
		self.assertEqual(new_investment.investment_renewal, amended.name)

	def test_changed_terms_need_a_reason_before_submit(self):
		unchanged = make_submitted_renewal(make_original_investment().name)
		frappe.get_doc("Investment", unchanged.new_investment).submit()

		renewal = make_submitted_renewal(self.investment.name)
		new_investment = frappe.get_doc("Investment", renewal.new_investment)
		new_investment.rate_of_interest = 8
		new_investment.save()

		self.assertEqual(frappe.db.get_value("Investment Renewal", renewal.name, "new_terms_changed"), 1)
		self.assertRaises(frappe.ValidationError, new_investment.submit)

		renewal.reload()
		renewal.reason_for_change = "Bank raised the rate to 8%"
		renewal.save()
		new_investment.reload()
		new_investment.submit()


def make_original_investment():
	investment = make_submitted_investment()
	make_transaction(investment.name, "Purchase", gross_amount=100000).submit()
	return investment


def amend_renewal(renewal):
	amended = frappe.copy_doc(renewal)
	amended.docstatus = 0
	amended.amended_from = renewal.name
	return amended.insert().submit()


def make_submitted_renewal(original_investment):
	make_transaction(original_investment, "Maturity", gross_amount=100000).submit()
	return make_renewal(original_investment, principal_renewed=100000).insert().submit()


def make_renewal(original_investment, **args):
	renewal = frappe.get_doc(
		{
			"doctype": "Investment Renewal",
			"original_investment": original_investment,
			"renewal_date": add_days(nowdate(), 1),
		}
	)
	renewal.update(args)
	return renewal
