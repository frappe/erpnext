# Copyright (c) 2026, Aagnya Mistry and contributors
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

		self.investment = make_submitted_investment()
		make_transaction(self.investment.name, "Purchase", gross_amount=100000).submit()

	def test_renewal_needs_approved_investment(self):
		cancelled_investment = make_submitted_investment()
		cancelled_investment.cancel()

		renewal = make_renewal(cancelled_investment.name, principal_renewed=1000)
		self.assertRaises(frappe.ValidationError, renewal.insert)

	def test_renewal_type_is_set_from_instrument(self):
		renewal = make_renewal(self.investment.name, principal_renewed=1000).insert()

		self.assertEqual(renewal.renewal_type, "Auto Renewal")

	def test_cannot_renew_more_than_paid_out(self):
		make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()

		renewal = make_renewal(self.investment.name, principal_renewed=100001).insert()
		self.assertRaises(frappe.ValidationError, renewal.submit)

	def test_cannot_renew_interest_not_received(self):
		make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()

		renewal = make_renewal(self.investment.name, principal_renewed=100000, interest_renewed=500).insert()
		self.assertRaises(frappe.ValidationError, renewal.submit)

	def test_cannot_renew_same_proceeds_twice(self):
		make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()
		make_renewal(self.investment.name, principal_renewed=60000).insert().submit()

		renewal = make_renewal(self.investment.name, principal_renewed=50000).insert()
		self.assertRaises(frappe.ValidationError, renewal.submit)

	def test_submit_creates_draft_new_investment(self):
		renewal = make_submitted_renewal(self.investment.name)
		new_investment = frappe.get_doc("Investment", renewal.new_investment)

		self.assertEqual(new_investment.docstatus, 0)
		self.assertEqual(new_investment.investment_renewal, renewal.name)
		self.assertEqual(
			frappe.db.get_value("Investment Renewal", renewal.name, "new_investment"), new_investment.name
		)

	def test_new_investment_keeps_tenure_and_renewed_amount(self):
		renewal = make_submitted_renewal(self.investment.name)
		new_investment = frappe.get_doc("Investment", renewal.new_investment)

		self.assertEqual(getdate(new_investment.purchase_date), getdate(renewal.renewal_date))
		self.assertEqual(new_investment.approved_amount, 100000)
		self.assertEqual(new_investment.principal_amount, 100000)
		self.assertEqual(
			date_diff(new_investment.maturity_date, new_investment.purchase_date),
			date_diff(self.investment.maturity_date, self.investment.purchase_date),
		)

	def test_renewal_allows_only_one_new_investment(self):
		renewal = make_submitted_renewal(self.investment.name)

		self.assertRaises(frappe.ValidationError, make_new_investment, renewal.name)

	def test_new_investment_needs_submitted_renewal(self):
		make_transaction(self.investment.name, "Maturity", gross_amount=100000).submit()
		renewal = make_renewal(self.investment.name, principal_renewed=100000).insert()

		self.assertRaises(frappe.ValidationError, make_new_investment, renewal.name)

	def test_cannot_cancel_renewal_with_draft_new_investment(self):
		renewal = make_submitted_renewal(self.investment.name)

		renewal.reload()
		self.assertRaises(frappe.ValidationError, renewal.cancel)
		self.assertTrue(frappe.db.exists("Investment", renewal.new_investment))

	def test_renewal_can_be_cancelled_once_draft_is_deleted(self):
		renewal = make_submitted_renewal(self.investment.name)
		frappe.delete_doc("Investment", renewal.new_investment)

		renewal.reload()
		renewal.cancel()

		self.assertEqual(renewal.docstatus, 2)

	def test_cannot_cancel_renewal_with_submitted_new_investment(self):
		renewal = make_submitted_renewal(self.investment.name)
		frappe.get_doc("Investment", renewal.new_investment).submit()

		renewal.reload()
		self.assertRaises(frappe.ValidationError, renewal.cancel)

	def test_cancelling_renewal_keeps_cancelled_new_investment(self):
		renewal = make_submitted_renewal(self.investment.name)
		new_investment = frappe.get_doc("Investment", renewal.new_investment)
		new_investment.submit()
		new_investment.cancel()

		renewal.reload()
		renewal.cancel()

		self.assertEqual(frappe.db.get_value("Investment", new_investment.name, "docstatus"), 2)

	def test_amended_renewal_creates_new_draft(self):
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

	def test_amended_renewal_draft_amends_cancelled_investment(self):
		renewal = make_submitted_renewal(self.investment.name)
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

	def test_deleting_draft_new_investment_frees_renewal(self):
		renewal = make_submitted_renewal(self.investment.name)

		frappe.delete_doc("Investment", renewal.new_investment)

		self.assertFalse(frappe.db.get_value("Investment Renewal", renewal.name, "new_investment"))
		make_new_investment(renewal.name).insert()

	def test_changed_rate_sets_new_terms_changed(self):
		renewal = make_submitted_renewal(self.investment.name)
		new_investment = frappe.get_doc("Investment", renewal.new_investment)

		new_investment.rate_of_interest = 8
		new_investment.save()

		self.assertEqual(frappe.db.get_value("Investment Renewal", renewal.name, "new_terms_changed"), 1)

	def test_changed_terms_need_a_reason_before_submit(self):
		renewal = make_submitted_renewal(self.investment.name)
		new_investment = frappe.get_doc("Investment", renewal.new_investment)
		new_investment.rate_of_interest = 8
		new_investment.save()

		self.assertRaises(frappe.ValidationError, new_investment.submit)

		renewal.reload()
		renewal.terms_change_reason = "Bank raised the rate to 8%"
		renewal.save()
		new_investment.reload()
		new_investment.submit()

	def test_unchanged_terms_need_no_reason(self):
		renewal = make_submitted_renewal(self.investment.name)

		frappe.get_doc("Investment", renewal.new_investment).submit()


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
