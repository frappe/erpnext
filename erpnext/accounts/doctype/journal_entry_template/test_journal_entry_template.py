# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


class TestJournalEntryTemplate(ERPNextTestSuite):
	"""Journal Entry Template's only real rule is validate_party: party_type is
	allowed only on Receivable/Payable accounts, and a party needs a party_type."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_template(self, rows, company=COMPANY):
		doc = frappe.new_doc("Journal Entry Template")
		doc.template_title = f"_Test JET {frappe.generate_hash(length=6)}"
		doc.company = company
		doc.voucher_type = "Journal Entry"
		doc.naming_series = frappe.get_meta("Journal Entry").get_field("naming_series").options.split("\n")[0]
		for row in rows:
			doc.append("accounts", row)
		return doc

	def test_party_type_only_on_receivable_or_payable_account(self):
		# Cash is neither Receivable nor Payable, so a party_type here is invalid
		doc = self.make_template([{"account": "Cash - _TC", "party_type": "Customer"}])
		self.assertRaises(frappe.ValidationError, doc.validate)

	def test_party_requires_party_type(self):
		doc = self.make_template([{"account": "Debtors - _TC", "party": "_Test Customer"}])
		self.assertRaises(frappe.ValidationError, doc.validate)

	def test_account_from_other_company_is_rejected(self):
		other_receivable = frappe.db.get_value(
			"Account", {"company": "_Test Company 1", "account_type": "Receivable", "is_group": 0}, "name"
		)
		self.assertTrue(other_receivable, "need a receivable account in _Test Company 1")
		doc = self.make_template(
			[{"account": other_receivable, "party_type": "Customer", "party": "_Test Customer"}]
		)
		self.assertRaises(frappe.ValidationError, doc.insert)
