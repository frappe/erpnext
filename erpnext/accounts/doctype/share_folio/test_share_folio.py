# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase


class TestShareFolio(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint("share_folio_test")
		self.addCleanup(frappe.db.rollback, save_point="share_folio_test")

	def test_company_cannot_have_two_treasury_folios(self):
		with patch.dict(frappe.flags, {"creating_share_folio": True}):
			self.make_treasury_folio().insert(ignore_permissions=True)
			with self.assertRaisesRegex(frappe.ValidationError, "treasury folio already exists"):
				self.make_treasury_folio().insert(ignore_permissions=True)

	def test_database_rejects_duplicate_folio_number_in_company(self):
		with patch.dict(frappe.flags, {"creating_share_folio": True}):
			folio = self.make_treasury_folio().insert(ignore_permissions=True)
		duplicate = self.make_treasury_folio()
		duplicate.name = "_Test Duplicate Folio Number"
		duplicate.folio_number = folio.folio_number
		with self.assertRaises(frappe.UniqueValidationError):
			duplicate.db_insert()

	def make_treasury_folio(self):
		return frappe.get_doc({"doctype": "Share Folio", "company": "_Test Company", "is_treasury": 1})
