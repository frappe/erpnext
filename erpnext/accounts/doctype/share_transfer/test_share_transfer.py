# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.share_transfer.share_transfer import ShareDontExists
from erpnext.tests.utils import ERPNextTestSuite


class TestShareTransfer(ERPNextTestSuite):
	def setUp(self):
		share_transfers = [
			{
				"doctype": "Share Transfer",
				"transfer_type": "Issue",
				"date": "2018-01-01",
				"to_shareholder": "SH-00001",
				"share_type": "Equity",
				"from_no": 1,
				"to_no": 500,
				"no_of_shares": 500,
				"rate": 10,
				"company": "_Test Company",
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC",
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-02",
				"from_shareholder": "SH-00001",
				"to_shareholder": "SH-00002",
				"share_type": "Equity",
				"from_no": 101,
				"to_no": 200,
				"no_of_shares": 100,
				"rate": 15,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC",
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-03",
				"from_shareholder": "SH-00001",
				"to_shareholder": "SH-00003",
				"share_type": "Equity",
				"from_no": 201,
				"to_no": 500,
				"no_of_shares": 300,
				"rate": 20,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC",
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-04",
				"from_shareholder": "SH-00003",
				"to_shareholder": "SH-00002",
				"share_type": "Equity",
				"from_no": 201,
				"to_no": 400,
				"no_of_shares": 200,
				"rate": 15,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC",
			},
			{
				"doctype": "Share Transfer",
				"transfer_type": "Purchase",
				"date": "2018-01-05",
				"from_shareholder": "SH-00003",
				"share_type": "Equity",
				"from_no": 401,
				"to_no": 500,
				"no_of_shares": 100,
				"rate": 25,
				"company": "_Test Company",
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC",
			},
		]
		for d in share_transfers:
			st = frappe.get_doc(d)
			st.submit()

	def test_fractional_rate_submission_after_reload(self):
		for rate, amount in ((10.1, 30.3), (0.1, 0.3), (10.25, 30.75)):
			with self.subTest(rate=rate):
				doc = frappe.get_doc(
					{
						"doctype": "Share Transfer",
						"transfer_type": "Issue",
						"date": "2018-01-06",
						"to_shareholder": "SH-00001",
						"share_type": "Equity",
						"from_no": 501,
						"to_no": 503,
						"no_of_shares": 3,
						"rate": rate,
						"amount": rate * 3,
						"company": "_Test Company",
						"asset_account": "Cash - _TC",
						"equity_or_liability_account": "Creditors - _TC",
					}
				).insert()
				self.assertEqual(doc.amount, amount)
				doc.reload()
				self.assertEqual(doc.amount, amount)
				doc.save()
				doc.reload()
				doc.submit()
				doc.reload()
				self.assertEqual(doc.docstatus, 1)
				self.assertEqual(doc.amount, amount)
				doc.cancel()
				self.assertEqual(doc.docstatus, 2)

	def test_issue_rejects_overlapping_share_ranges(self):
		issue = frappe.get_doc(
			{
				"doctype": "Share Transfer",
				"transfer_type": "Issue",
				"date": "2018-01-06",
				"to_shareholder": "SH-00001",
				"share_type": "Equity",
				"from_no": 600,
				"to_no": 700,
				"no_of_shares": 101,
				"rate": 10,
				"company": "_Test Company",
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC",
			}
		).submit()

		for from_no, to_no in (
			(550, 750),
			(550, 650),
			(650, 750),
			(625, 675),
			(600, 700),
			(550, 600),
			(700, 750),
		):
			with self.subTest(from_no=from_no, to_no=to_no):
				duplicate = frappe.copy_doc(issue)
				duplicate.update(
					{
						"to_shareholder": "SH-00002",
						"to_folio_no": frappe.db.get_value("Shareholder", "SH-00002", "folio_no"),
						"from_no": from_no,
						"to_no": to_no,
						"no_of_shares": to_no - from_no + 1,
						"amount": 0,
					}
				)
				with self.assertRaisesRegex(frappe.DuplicateEntryError, "The shares already exist"):
					duplicate.submit()

		self.assertEqual(
			[(row.from_no, row.to_no) for row in issue.get_company_shareholder().share_balance],
			[(1, 400), (600, 700)],
		)
		self.assertEqual(
			[(row.from_no, row.to_no) for row in frappe.get_doc("Shareholder", "SH-00002").share_balance],
			[(101, 200), (201, 400)],
		)

		for from_no, to_no in ((550, 599), (701, 750)):
			with self.subTest(from_no=from_no, to_no=to_no):
				adjacent = frappe.copy_doc(issue)
				adjacent.update(
					{"from_no": from_no, "to_no": to_no, "no_of_shares": to_no - from_no + 1, "amount": 0}
				)
				adjacent.submit()
				self.assertEqual(adjacent.docstatus, 1)
				adjacent.cancel()

	def test_shareholders_stay_protected_after_buyback(self):
		from frappe.client import set_value

		for shareholder, from_no, to_no in (
			("SH-00001", 1, 100),
			("SH-00002", 101, 200),
			("SH-00002", 201, 400),
		):
			purchase = frappe.get_doc(
				{
					"doctype": "Share Transfer",
					"transfer_type": "Purchase",
					"date": "2018-01-06",
					"from_shareholder": shareholder,
					"share_type": "Equity",
					"from_no": from_no,
					"to_no": to_no,
					"no_of_shares": to_no - from_no + 1,
					"rate": 10,
					"company": "_Test Company",
					"asset_account": "Cash - _TC",
					"equity_or_liability_account": "Creditors - _TC",
				}
			).submit()

		company_shareholder = frappe.get_doc("Shareholder", {"company": "_Test Company", "is_company": 1})
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "share-register@example.com",
				"first_name": "Share Register",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert()
		with self.set_user(user.name):
			for name in (company_shareholder.name, "SH-00001", "SH-00002", "SH-00003"):
				shareholder = frappe.get_doc("Shareholder", name)
				self.assertFalse(shareholder.share_balance)
				set_value("Shareholder", name, "title", "Share Register")
				for changes in (
					{"is_company": 1 - shareholder.is_company},
					{"company": "_Test Company 1"},
					{"company": "_Test Company 1", "is_company": 1 - shareholder.is_company},
				):
					with self.subTest(shareholder=name, changes=changes):
						with self.assertRaisesRegex(frappe.ValidationError, "Cannot change the company"):
							set_value("Shareholder", name, changes)

				shareholder.reload()
				self.assertEqual(shareholder.company, "_Test Company")
				self.assertEqual(shareholder.is_company, int(name == company_shareholder.name))
				self.assertEqual(shareholder.title, "Share Register")
				with self.assertRaisesRegex(frappe.ValidationError, "Cannot delete a shareholder"):
					shareholder.delete()

		purchase.cancel()
		shareholder = frappe.get_doc("Shareholder", "SH-00002")
		self.assertEqual(shareholder.company, "_Test Company")
		self.assertEqual([(row.from_no, row.to_no) for row in shareholder.share_balance], [(201, 400)])

	def test_invalid_share_transfer(self):
		doc = frappe.get_doc(
			{
				"doctype": "Share Transfer",
				"transfer_type": "Transfer",
				"date": "2018-01-05",
				"from_shareholder": "SH-00003",
				"to_shareholder": "SH-00002",
				"share_type": "Equity",
				"from_no": 1,
				"to_no": 100,
				"no_of_shares": 100,
				"rate": 15,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC",
			}
		)
		self.assertRaises(ShareDontExists, doc.insert)

		doc = frappe.get_doc(
			{
				"doctype": "Share Transfer",
				"transfer_type": "Purchase",
				"date": "2018-01-02",
				"from_shareholder": "SH-00001",
				"share_type": "Equity",
				"from_no": 1,
				"to_no": 200,
				"no_of_shares": 200,
				"rate": 15,
				"company": "_Test Company",
				"asset_account": "Cash - _TC",
				"equity_or_liability_account": "Creditors - _TC",
			}
		)
		self.assertRaises(ShareDontExists, doc.insert)


class TestShareTransferValidation(ERPNextTestSuite):
	"""basic_validations() enforces the transfer's internal consistency. Exercised
	directly (to_folio_no set to skip folio auto-naming) so no shareholder fixtures
	are needed - it only reasons about the document's own fields."""

	def make_transfer(self, **overrides):
		doc = frappe.new_doc("Share Transfer")
		doc.update(
			{
				"transfer_type": "Transfer",
				"date": "2026-01-01",
				"from_shareholder": "SH-A",
				"to_shareholder": "SH-B",
				"to_folio_no": "1",
				"share_type": "Equity",
				"from_no": 1,
				"to_no": 100,
				"no_of_shares": 100,
				"rate": 10,
				"amount": 1000,
				"company": "_Test Company",
				"equity_or_liability_account": "Creditors - _TC",
			}
		)
		doc.update(overrides)
		return doc

	def test_baseline_transfer_is_consistent(self):
		# the helper's defaults must pass, otherwise the negative cases prove nothing
		self.make_transfer().basic_validations()

	def test_seller_and_buyer_must_differ(self):
		doc = self.make_transfer(to_shareholder="SH-A")
		self.assertRaises(frappe.ValidationError, doc.basic_validations)

	def test_share_count_must_match_the_number_range(self):
		# 1..100 is 100 shares, not 50
		doc = self.make_transfer(no_of_shares=50)
		self.assertRaises(frappe.ValidationError, doc.basic_validations)

	def test_amount_must_equal_rate_times_shares(self):
		doc = self.make_transfer(amount=999)  # 10 * 100 = 1000
		self.assertRaises(frappe.ValidationError, doc.basic_validations)

	def test_amount_is_derived_when_left_blank(self):
		doc = self.make_transfer(amount=0)
		doc.basic_validations()
		self.assertEqual(doc.amount, 1000)

	def test_equity_or_liability_account_is_required(self):
		doc = self.make_transfer(equity_or_liability_account=None)
		self.assertRaises(frappe.ValidationError, doc.basic_validations)

	def test_issue_requires_a_to_shareholder(self):
		doc = self.make_transfer(transfer_type="Issue", to_shareholder="", asset_account="Cash - _TC")
		self.assertRaises(frappe.ValidationError, doc.basic_validations)

	def test_purchase_requires_a_from_shareholder(self):
		doc = self.make_transfer(transfer_type="Purchase", from_shareholder="", asset_account="Cash - _TC")
		self.assertRaises(frappe.ValidationError, doc.basic_validations)
