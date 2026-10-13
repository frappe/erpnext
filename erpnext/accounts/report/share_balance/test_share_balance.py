# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.report.share_balance.share_balance import execute
from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareBalanceReport(ShareholdingTestCase):
	def test_historical_balances_after_transfer_and_return(self):
		holder = self.create_shareholder()
		other = self.create_shareholder()
		self.create_transaction(
			transaction_type="Issue",
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=100,
			face_value_per_share=10,
			rate_per_share=15,
			posting_date=add_days(nowdate(), -3),
		)
		self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=holder,
			to_shareholder=other,
			from_share_number=1,
			to_share_number=40,
			posting_date=add_days(nowdate(), -2),
		)
		self.create_transaction(
			transaction_type="Transfer",
			from_shareholder=other,
			to_shareholder=holder,
			from_share_number=1,
			to_share_number=40,
			posting_date=add_days(nowdate(), -1),
		)
		for days, quantity in ((-3, 100), (-2, 60), (-1, 100)):
			rows = execute(
				frappe._dict(company=self.company, shareholder=holder, date=add_days(nowdate(), days))
			)[1]
			self.assertEqual(len(rows), 1)
			self.assertEqual(rows[0].quantity, quantity)
			self.assertEqual(rows[0].total_face_value, quantity * 10)
		self.assertEqual(
			execute(frappe._dict(company=self.company, shareholder=holder, date=add_days(nowdate(), -4)))[1],
			[],
		)
