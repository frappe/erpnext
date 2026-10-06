# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.regional.italy.utils import get_e_invoice_attachments, set_payment_schedule_swift_number
from erpnext.tests.utils import ERPNextTestSuite


class TestItalyUtils(ERPNextTestSuite):
	def test_set_payment_schedule_swift_number_reads_bank(self):
		# the SWIFT code lives on Bank, not on Bank Account: it is read through the account's bank
		values = {
			("Bank Account", "_Test Bank Account", "bank"): "_Test Bank",
			("Bank", "_Test Bank", "swift_number"): "BCITITMM",
		}
		doc = frappe._dict(
			payment_schedule=[
				frappe._dict(bank_account="_Test Bank Account"),
				frappe._dict(bank_account=None, bank_account_swift_number="STALE"),
			]
		)

		with patch("frappe.get_cached_value", side_effect=lambda *args: values.get(args)):
			set_payment_schedule_swift_number(doc)

		self.assertEqual(doc.payment_schedule[0].bank_account_swift_number, "BCITITMM")
		self.assertIsNone(doc.payment_schedule[1].bank_account_swift_number)

	def test_get_e_invoice_attachments_finds_existing_xml(self):
		# the existing XML must be found, otherwise `replace=True` adds a second one
		invoice = frappe._dict(name="_Test Italy E-Invoice 0001", company_tax_id="01234567890")
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "IT01234567890_00001.xml",
				"attached_to_doctype": "Sales Invoice",
				"attached_to_name": invoice.name,
				"content": "<FatturaElettronica/>",
				"is_private": 1,
			}
		).insert(ignore_permissions=True)

		self.assertEqual([attachment.name for attachment in get_e_invoice_attachments(invoice)], [file.name])
