# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.report.cheques_and_deposits_incorrectly_cleared.cheques_and_deposits_incorrectly_cleared import (
	execute,
)


class TestChequesAndDepositsIncorrectlyCleared(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_payment_entry_direction_follows_bank_side(self):
		report_date = add_days(nowdate(), -2)
		transfer_in = self.make_cleared_payment("Internal Transfer", "Cash - _TC", "_Test Bank - _TC", 2000)
		paid_out = self.make_cleared_payment("Pay", "_Test Bank - _TC", "Creditors - _TC", 300)

		rows = self.get_rows(report_date)

		self.assertEqual((rows[transfer_in].debit, rows[transfer_in].credit), (2000, 0))
		self.assertEqual((rows[paid_out].debit, rows[paid_out].credit), (0, 300))

	def make_cleared_payment(self, payment_type: str, paid_from: str, paid_to: str, amount: float) -> str:
		if payment_type == "Internal Transfer":
			payment = self.make_internal_transfer(paid_from, paid_to, amount)
		else:
			payment = create_payment_entry(
				payment_type=payment_type, paid_from=paid_from, paid_to=paid_to, paid_amount=amount
			)
		payment.submit()
		payment.db_set("clearance_date", add_days(nowdate(), -5))
		return payment.name

	def make_internal_transfer(self, paid_from: str, paid_to: str, amount: float):
		return frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"company": "_Test Company",
				"payment_type": "Internal Transfer",
				"paid_from": paid_from,
				"paid_to": paid_to,
				"paid_amount": amount,
				"received_amount": amount,
				"reference_no": "Test001",
				"reference_date": nowdate(),
			}
		).insert()

	def get_rows(self, report_date: str) -> dict:
		filters = frappe._dict(company="_Test Company", account="_Test Bank - _TC", report_date=report_date)
		return {row.payment_entry: row for row in execute(filters)[1]}
