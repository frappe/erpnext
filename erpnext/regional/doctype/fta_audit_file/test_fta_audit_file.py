# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestFTAAuditFile(FrappeTestCase):
	def setUp(self):
		"""Create a UAE test company with TRN before each test.

		Per-test creation (not setUpClass) because FrappeTestCase rolls
		back the database after each test, including class-level fixtures.
		"""
		self.company = self._get_or_create_test_company()

	def _get_or_create_test_company(self):
		company_name = "_Test Company UAE"
		if not frappe.db.exists("Company", company_name):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"abbr": "_TCU",
					"country": "United Arab Emirates",
					"default_currency": "AED",
					"tax_id": "100123456789012",
				}
			).insert(ignore_permissions=True)
		else:
			company = frappe.get_doc("Company", company_name)
			if not company.tax_id:
				company.tax_id = "100123456789012"
				company.save(ignore_permissions=True)
		return company_name

	def test_fta_audit_file_creation(self):
		"""Test that FTA Audit File can be created."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2024-01-01",
				"to_date": "2024-03-31",
				"file_type": "VAT",
			}
		)
		doc.insert()

		self.assertTrue(doc.name)
		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.file_type, "VAT")

	def test_date_validation(self):
		"""Test that from_date cannot be after to_date."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2024-03-31",
				"to_date": "2024-01-01",
				"file_type": "VAT",
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_company_trn_validation(self):
		"""Test that company must have a TRN."""
		company_no_trn = "_Test Company No TRN"

		if not frappe.db.exists("Company", company_no_trn):
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_no_trn,
					"abbr": "_TCNT",
					"country": "United Arab Emirates",
					"default_currency": "AED",
				}
			)
			company.insert(ignore_permissions=True)

		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": company_no_trn,
				"from_date": "2024-01-01",
				"to_date": "2024-03-31",
				"file_type": "VAT",
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_generate_faf_empty_period(self):
		"""End-to-end smoke test: generate against an empty period.

		With ``frappe.flags.in_test`` set by FrappeTestCase, the enqueued
		job runs synchronously, so by the time generate_faf() returns the
		doc has reached its terminal status.
		"""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2099-01-01",
				"to_date": "2099-01-31",
				"file_type": "VAT",
			}
		)
		doc.insert()

		result = doc.generate_faf()
		self.assertTrue(result["success"])

		doc.reload()
		self.assertEqual(doc.status, "Generated")
		self.assertTrue(doc.faf_file)

		self.assertIn("Company Information written", doc.generation_log)
		self.assertIn("Purchase Listing written", doc.generation_log)
		self.assertIn("Supply Listing written", doc.generation_log)
		self.assertIn("General Ledger written", doc.generation_log)

	def test_generate_faf_csv_structure(self):
		"""The generated CSV must contain the four spec section markers."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2099-02-01",
				"to_date": "2099-02-28",
				"file_type": "VAT",
			}
		)
		doc.insert()
		doc.generate_faf()
		doc.reload()
		self.assertEqual(doc.status, "Generated")

		file_doc = frappe.get_doc("File", {"file_url": doc.faf_file})
		csv_content = file_doc.get_content()
		if isinstance(csv_content, bytes):
			csv_content = csv_content.decode("utf-8")
		for marker in (
			"CompInfoStart",
			"CompInfoEnd",
			"PurcDataStart",
			"PurcDataEnd",
			"SuppDataStart",
			"SuppDataEnd",
			"GLDataStart",
			"GLDataEnd",
		):
			self.assertIn(marker, csv_content, f"Missing FAF section marker {marker!r}")

		self.assertIn("FAFv1.0.0", csv_content)

	def test_tax_agent_fields_appear_in_company_info(self):
		"""Tax Agency / Tax Agent details must round-trip into the CSV."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2099-04-01",
				"to_date": "2099-04-30",
				"file_type": "VAT",
				"tax_agency_name": "Acme Tax Agency",
				"tan": "TAN-555-001",
				"tax_agent_name": "Jane Auditor",
				"taan": "TAAN-777",
			}
		)
		doc.insert()
		doc.generate_faf()
		doc.reload()
		self.assertEqual(doc.status, "Generated")

		file_doc = frappe.get_doc("File", {"file_url": doc.faf_file})
		csv_content = file_doc.get_content()
		if isinstance(csv_content, bytes):
			csv_content = csv_content.decode("utf-8")

		for value in ("Acme Tax Agency", "TAN-555-001", "Jane Auditor", "TAAN-777"):
			self.assertIn(value, csv_content, f"Missing tax-agent value {value!r} in FAF")

	def test_decimal_fields_use_two_decimal_places(self):
		"""Decimal[14,2] cells must always emit two decimal places per spec."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2099-05-01",
				"to_date": "2099-05-31",
				"file_type": "VAT",
			}
		)
		doc.insert()
		doc.generate_faf()
		doc.reload()

		file_doc = frappe.get_doc("File", {"file_url": doc.faf_file})
		csv_content = file_doc.get_content()
		if isinstance(csv_content, bytes):
			csv_content = csv_content.decode("utf-8")

		self.assertIn("PurcDataEnd,0.00,0.00,0", csv_content)
		self.assertIn("SuppDataEnd,0.00,0.00,0", csv_content)
		self.assertIn("GLDataEnd,0.00,0.00,0,AED", csv_content)

		self.assertNotIn("PurcDataEnd,0.0,", csv_content)
		self.assertNotIn("SuppDataEnd,0.0,", csv_content)
		self.assertNotIn("GLDataEnd,0.0,", csv_content)

	def test_generate_faf_excise_not_yet_implemented(self):
		"""Excise FAF (Appendix 6) should error cleanly until implemented."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2099-03-01",
				"to_date": "2099-03-31",
				"file_type": "Excise",
			}
		)
		doc.insert()

		self.assertRaises(frappe.ValidationError, doc.generate_faf)
		doc.reload()
		self.assertEqual(doc.status, "Error")

	def test_mark_as_submitted_workflow(self):
		"""Generated docs can be marked submitted; non-Generated cannot."""
		doc = frappe.get_doc(
			{
				"doctype": "FTA Audit File",
				"company": self.company,
				"from_date": "2099-05-01",
				"to_date": "2099-05-31",
				"file_type": "VAT",
			}
		)
		doc.insert()

		self.assertRaises(frappe.ValidationError, doc.mark_as_submitted)

		doc.generate_faf()
		doc.reload()
		self.assertEqual(doc.status, "Generated")

		result = doc.mark_as_submitted()
		self.assertTrue(result["success"])
		doc.reload()
		self.assertEqual(doc.status, "Submitted")

	def tearDown(self):
		frappe.db.rollback()
