# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
TAX_ACCOUNT = "_Test Account VAT - _TC"
RECEIVABLE_ACCOUNT = "Debtors - _TC"


class TestItemTaxTemplate(ERPNextTestSuite):
	"""Item Tax Template validates its tax rows: each account must belong to the
	company, be a tax-like account type, and appear only once."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_template(self, rows, title="_Test ITT"):
		doc = frappe.new_doc("Item Tax Template")
		doc.title = f"{title} {frappe.generate_hash(length=6)}"
		doc.company = COMPANY
		for account, rate, not_applicable in rows:
			doc.append(
				"taxes",
				{"tax_type": account, "tax_rate": rate, "not_applicable": not_applicable},
			)
		return doc

	def test_valid_template_saves_and_is_named_with_abbr(self):
		doc = self.make_template([(TAX_ACCOUNT, 9, 0)])
		doc.insert()
		self.assertTrue(doc.name.endswith(" - _TC"))
		self.assertTrue(doc.name.startswith(doc.title))

	def test_duplicate_tax_type_throws(self):
		doc = self.make_template([(TAX_ACCOUNT, 9, 0), (TAX_ACCOUNT, 5, 0)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_account_of_wrong_company_throws(self):
		other_account = frappe.db.get_value("Account", {"company": "_Test Company 1", "is_group": 0}, "name")
		self.assertTrue(other_account, "need a non-group account in _Test Company 1")
		doc = self.make_template([(other_account, 9, 0)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_disallowed_account_type_throws(self):
		# a Receivable account is not Tax/Chargeable/Income/Expense
		doc = self.make_template([(RECEIVABLE_ACCOUNT, 9, 0)])
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_not_applicable_row_has_rate_zeroed(self):
		doc = self.make_template([(TAX_ACCOUNT, 18, 1)])
		doc.insert()
		self.assertEqual(doc.taxes[0].tax_rate, 0)

	def test_negative_tax_rate_is_accepted(self):
		# SUSPECTED BUG: validate never bounds tax_rate, so a negative (or >100) rate
		# saves silently. Locking the current (wrong) behaviour.
		doc = self.make_template([(TAX_ACCOUNT, -5, 0)])
		doc.insert()
		self.assertEqual(doc.taxes[0].tax_rate, -5)
