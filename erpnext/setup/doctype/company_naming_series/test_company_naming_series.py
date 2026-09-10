# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.setup.doctype.company_naming_series.company_naming_series import (
	get_allowed_naming_series,
)
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
ALLOWED_SERIES = "ACC-JV-.YYYY.-"
SERIES = "TEST-NAMING-.YYYY.-"


class TestCompanyNamingSeries(ERPNextTestSuite):
	def setUp(self):
		self.company = frappe.get_doc("Company", COMPANY)
		self.company.set("document_naming_series", [])

	def restrict(self, document_type, options):
		self.company.append(
			"document_naming_series",
			{"document_type": document_type, "naming_series_options": options},
		)
		self.company.save()

	def test_no_rows_means_every_series_is_offered(self):
		self.company.save()

		self.assertIsNone(get_allowed_naming_series(COMPANY, "Journal Entry"))

	def test_allowed_series_are_read_off_the_company(self):
		self.restrict("Journal Entry", "ACC-JV-.YYYY.-")

		self.assertEqual(get_allowed_naming_series(COMPANY, "Journal Entry"), ["ACC-JV-.YYYY.-"])
		self.assertIsNone(get_allowed_naming_series(COMPANY, "Sales Invoice"))

	def test_a_series_dropped_from_the_doctype_stops_being_allowed(self):
		self.restrict("Journal Entry", ALLOWED_SERIES)
		self.assertEqual(get_allowed_naming_series(COMPANY, "Journal Entry"), [ALLOWED_SERIES])

		with self.patch_naming_series_options("Journal Entry", []):
			self.assertEqual(get_allowed_naming_series(COMPANY, "Journal Entry"), [])
			self.assertRaises(frappe.ValidationError, build_journal_entry(ALLOWED_SERIES).insert)

	def patch_naming_series_options(self, doctype, options):
		return patch.object(frappe.get_meta(doctype), "get_naming_series_options", return_value=options)

	def test_series_must_be_one_the_document_type_offers(self):
		self.assertRaises(frappe.ValidationError, self.restrict, "Journal Entry", SERIES)

	def test_document_type_must_use_a_naming_series(self):
		self.assertRaises(frappe.ValidationError, self.restrict, "Company", "ANY-.####.")

	def test_document_type_cannot_repeat(self):
		self.company.append(
			"document_naming_series",
			{"document_type": "Journal Entry", "naming_series_options": "ACC-JV-.YYYY.-"},
		)
		self.assertRaises(frappe.ValidationError, self.restrict, "Journal Entry", "ACC-JV-.YYYY.-")

	def test_disallowed_series_is_rejected_on_insert(self):
		self.restrict("Journal Entry", ALLOWED_SERIES)

		entry = build_journal_entry(SERIES)
		self.assertRaises(frappe.ValidationError, entry.insert)

		entry = build_journal_entry(ALLOWED_SERIES)
		entry.insert()
		self.assertTrue(entry.name.startswith("ACC-JV-"))

	def test_an_unrestricted_document_type_keeps_every_series(self):
		self.restrict("Journal Entry", ALLOWED_SERIES)

		invoice = create_sales_invoice(do_not_save=True)
		invoice.insert()
		self.assertTrue(invoice.name.startswith("T-SINV-"))


def build_journal_entry(naming_series):
	entry = make_journal_entry("_Test Cash - _TC", "_Test Bank - _TC", 100, save=False)
	entry.naming_series = naming_series
	return entry
