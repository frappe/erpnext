# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase


class TestShareFolio(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("share_folio_test")
		self.addCleanup(frappe.db.rollback, save_point="share_folio_test")

	def test_folio_cannot_be_created_directly(self):
		with self.assertRaisesRegex(frappe.ValidationError, "created automatically"):
			self.make_treasury_folio().insert(ignore_permissions=True)

	def test_treasury_folio_clears_member_details_and_uses_document_number(self):
		folio = self.make_treasury_folio()
		folio.date_of_becoming_member = "2026-01-01"
		folio.date_of_cessation = "2026-01-02"
		with patch.dict(frappe.flags, {"creating_share_folio": True}):
			folio.insert(ignore_permissions=True)
		self.assertEqual(folio.folio_number, folio.name)
		self.assertIsNone(folio.shareholder)
		self.assertIsNone(folio.date_of_becoming_member)
		self.assertIsNone(folio.date_of_cessation)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be edited"):
			folio.save(ignore_permissions=True)

	def test_company_cannot_have_two_treasury_folios(self):
		with patch.dict(frappe.flags, {"creating_share_folio": True}):
			self.make_treasury_folio().insert(ignore_permissions=True)
			with self.assertRaisesRegex(frappe.ValidationError, "treasury folio already exists"):
				self.make_treasury_folio().insert(ignore_permissions=True)

	def test_non_treasury_folio_requires_shareholder(self):
		folio = self.make_treasury_folio()
		folio.is_treasury = 0
		with self.assertRaisesRegex(frappe.ValidationError, "Shareholder is required"):
			folio.validate_holder()

	def test_database_rejects_duplicate_folio_number_in_company(self):
		with patch.dict(frappe.flags, {"creating_share_folio": True}):
			folio = self.make_treasury_folio().insert(ignore_permissions=True)
		duplicate = self.make_treasury_folio()
		duplicate.name = "_Test Duplicate Folio Number"
		duplicate.folio_number = folio.folio_number
		with self.assertRaises(frappe.UniqueValidationError):
			duplicate.db_insert()

	def test_cessation_cannot_precede_membership(self):
		folio = self.make_treasury_folio()
		folio.date_of_becoming_member = "2026-01-02"
		folio.date_of_cessation = "2026-01-01"
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be before"):
			folio.validate_membership_dates()

	def make_treasury_folio(self):
		return frappe.get_doc({"doctype": "Share Folio", "company": "_Test Company", "is_treasury": 1})
