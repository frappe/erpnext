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
