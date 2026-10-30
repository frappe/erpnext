# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.translate import print_language
from frappe.utils import fmt_money, money_in_words, nowdate
from frappe.www.printview import get_rendered_template

from erpnext.accounts.doctype.cheque_print_template.cheque_print_template import (
	create_or_update_cheque_print_format,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestChequePrintTemplate(ERPNextTestSuite):
	def test_cheque_amount_currency_and_print_language(self):
		template = frappe.get_doc(
			doctype="Cheque Print Template", bank_name="_Test Cheque Currency", is_account_payable=0
		).insert()
		print_format = create_or_update_cheque_print_format(template.name)

		with self.change_settings("System Settings", {"number_format": "#,###.##"}), print_language("en"):
			for payment_type in ("Pay", "Receive", "Internal Transfer"):
				payment = frappe.get_doc(
					doctype="Payment Entry",
					company="_Test Company",
					payment_type=payment_type,
					paid_from="_Test Bank USD - _TC",
					paid_to="Creditors - _TC",
					paid_amount=100.25,
					received_amount=8020,
					source_exchange_rate=80,
					target_exchange_rate=1,
					reference_no="CHEQUE-1001",
					reference_date=nowdate(),
				)
				if payment_type == "Pay":
					payment.party_type = "Supplier"
					payment.party = "_Test Supplier"
				elif payment_type == "Receive":
					payment.update(
						{
							"party_type": "Customer",
							"party": "_Test Customer",
							"paid_from": "Debtors - _TC",
							"paid_to": "_Test Bank USD - _TC",
							"paid_amount": 8020,
							"received_amount": 100.25,
							"source_exchange_rate": 1,
							"target_exchange_rate": 80,
						}
					)
				else:
					payment.paid_to = "_Test Bank - _TC"
				payment.insert().submit()
				self.assertEqual(payment.in_words, money_in_words(100.25, "USD"))

				for language in ("en", "fr", "de"):
					with self.subTest(payment_type=payment_type, language=language), print_language(language):
						rendered = get_rendered_template(
							frappe.get_doc("Payment Entry", payment.name),
							print_format=print_format,
							no_letterhead=True,
						)
						self.assertIn(money_in_words(100.25, "USD"), rendered)
						self.assertIn(fmt_money(100.25, currency="USD"), rendered)
				self.assertEqual(payment.reload().in_words, money_in_words(100.25, "USD"))
