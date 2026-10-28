# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate

from erpnext.accounts.services.payment_schedule import get_payment_term_details
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentTerm(ERPNextTestSuite):
	def make_term(self, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "Payment Term",
				"payment_term_name": f"_Test Term {frappe.generate_hash(length=6)}",
				"invoice_portion": 100,
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": 30,
				**kwargs,
			}
		)

	def test_invalid_values_are_refused(self):
		for values in (
			{"invoice_portion": -20},
			{"invoice_portion": 150},
			{"credit_days": -15},
			{"discount": 150, "discount_type": "Percentage", "discount_validity": 10},
			{"discount": -5, "discount_type": "Amount", "discount_validity": 10},
			{"discount": 2, "discount_validity": -30},
		):
			with self.subTest(values=values):
				self.assertRaises(frappe.ValidationError, self.make_term(**values).insert)

	def test_discount_validity_after_due_date_is_refused(self):
		term = self.make_term(discount=2, discount_type="Percentage", discount_validity=40)
		self.assertRaisesRegex(frappe.ValidationError, "on or before the due date", term.insert)

		self.make_term(discount=2, discount_type="Percentage", discount_validity=10).insert()

	def test_discount_date_capped_at_due_date(self):
		# different bases cannot be compared on the term: the schedule caps the discount date
		term = self.make_term(
			credit_days=0,
			discount=2,
			discount_type="Percentage",
			discount_validity_based_on="Day(s) after the end of the invoice month",
			discount_validity=10,
		).insert()
		details = get_payment_term_details(term.name, posting_date="2026-10-01", grand_total=1000)
		self.assertEqual(getdate(details.due_date), getdate("2026-10-01"))
		self.assertEqual(getdate(details.discount_date), getdate(details.due_date))
		self.assertLess(getdate(details.discount_date), add_days(getdate("2026-10-31"), 10))
