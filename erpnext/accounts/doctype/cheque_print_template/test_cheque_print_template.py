# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.desk.form.load import get_meta_bundle
from frappe.translate import print_language
from frappe.utils import fmt_money, get_datetime, money_in_words, nowdate
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

	def test_generated_print_format_ownership(self):
		template = frappe.get_doc(
			doctype="Cheque Print Template", bank_name="_Test Cheque Format Ownership"
		).insert()

		for operation in ("rename", "delete"):
			with self.subTest(operation=operation):
				generated = create_or_update_cheque_print_format(template.name)
				template.reload()
				if operation == "rename":
					frappe.rename_doc("Print Format", generated.name, generated.name + " Archived")
				else:
					frappe.delete_doc("Print Format", generated.name)

				self.assertEqual(template.has_print_format, 1)
				replacement = frappe.get_doc(
					doctype="Print Format",
					name=template.name,
					doc_type="Payment Entry",
					standard="No",
					custom_format=1,
					print_format_type="Jinja",
					html="<h1>Payment remittance advice</h1>",
				).insert()
				with self.assertRaises(frappe.ValidationError):
					create_or_update_cheque_print_format(template.name)
				self.assertEqual(replacement.reload().html, "<h1>Payment remittance advice</h1>")
				# Reusing the generated HTML must not transfer ownership to the replacement record.
				replacement.html = generated.html
				replacement.save()
				with self.assertRaises(frappe.ValidationError):
					create_or_update_cheque_print_format(template.name)
				frappe.delete_doc("Print Format", replacement.name)

		generated = create_or_update_cheque_print_format(template.name)
		template.reload()
		template.payer_name_from_left_edge = 5
		template.save()
		updated = create_or_update_cheque_print_format(template.name)
		self.assertEqual(generated.name, updated.name)
		self.assertNotEqual(generated.html, updated.html)
		self.assertIn("left: 5.0cm", updated.html)

		# Existing generated formats can acquire an identity without changing their HTML.
		template.db_set("print_format_creation", None)
		self.assertEqual(create_or_update_cheque_print_format(template.name).html, updated.html)
		self.assertEqual(get_datetime(template.reload().print_format_creation), updated.creation)

		# An untracked customized format must not be adopted based on the stale checkbox.
		template.db_set("print_format_creation", None)
		updated.reload()
		updated.html = "<h1>Customized payment layout</h1>"
		updated.save()
		with self.assertRaises(frappe.ValidationError):
			create_or_update_cheque_print_format(template.name)
		self.assertEqual(updated.reload().html, "<h1>Customized payment layout</h1>")

		with self.set_user("Guest"), patch.dict(frappe.flags, {"in_test": False}):
			with self.assertRaises(frappe.PermissionError):
				create_or_update_cheque_print_format(template.name)
		self.assertEqual(updated.reload().html, "<h1>Customized payment layout</h1>")

	def test_print_format_identity_permissions(self):
		manager = frappe.get_doc(
			doctype="User",
			email="cheque-accounts-manager@example.com",
			first_name="Cheque Accounts Manager",
			enabled=1,
			send_welcome_email=0,
			roles=[{"role": "Accounts Manager"}],
		).insert()
		print_format = frappe.get_doc(
			doctype="Print Format",
			name="_Test Cheque Format Permissions",
			doc_type="Payment Entry",
			standard="No",
			custom_format=1,
			print_format_type="Jinja",
			html="<h1>Payment remittance advice</h1>",
		).insert()

		with self.set_user(manager.name):
			self.assertFalse(frappe.has_permission("Print Format", "write", doc=print_format))
			creation = next(
				row["creation"]
				for row in get_meta_bundle("Payment Entry")[0]["__print_formats"]
				if row["name"] == print_format.name
			)
			template = frappe.get_doc(
				doctype="Cheque Print Template",
				bank_name=print_format.name,
				has_print_format=1,
				print_format_creation=creation,
			).insert()
			self.assertFalse(template.reload().has_print_format)
			self.assertIsNone(template.print_format_creation)
			template.has_print_format = 1
			template.print_format_creation = creation
			template.save()
			self.assertFalse(template.reload().has_print_format)
			self.assertIsNone(template.print_format_creation)

		with self.set_user("test@example.com"):
			with self.assertRaises(frappe.ValidationError):
				create_or_update_cheque_print_format(template.name)
		self.assertEqual(print_format.reload().html, "<h1>Payment remittance advice</h1>")

		frappe.delete_doc("Print Format", print_format.name)
		with self.set_user("test@example.com"):
			generated = create_or_update_cheque_print_format(template.name)
		with self.set_user(manager.name):
			template.reload()
			template.payer_name_from_left_edge = 5
			template.has_print_format = 0
			template.print_format_creation = None
			template.save()
			self.assertTrue(template.reload().has_print_format)
			self.assertEqual(get_datetime(template.print_format_creation), get_datetime(generated.creation))
		with self.set_user("test@example.com"):
			self.assertIn("left: 5.0cm", create_or_update_cheque_print_format(template.name).html)
