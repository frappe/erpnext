# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe

from erpnext.accounts.doctype.share_transfer.share_transfer import ShareDontExists

test_dependencies = ["Share Type", "Shareholder"]


class TestShareTransfer(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabShare Transfer`")
		frappe.db.sql("delete from `tabShare Balance`")
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
