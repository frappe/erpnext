# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.crm.doctype.contract_template.contract_template import get_contract_template
from erpnext.tests.utils import ERPNextTestSuite


class TestContractTemplate(ERPNextTestSuite):
	"""Contract Template validates its Jinja terms and renders them against a doc."""

	def test_malformed_contract_terms_are_rejected(self):
		doc = frappe.new_doc("Contract Template")
		doc.contract_terms = "{% for x in %}"  # invalid Jinja
		self.assertRaises(frappe.ValidationError, doc.validate)

		# a valid template, and no template at all, both pass
		doc.contract_terms = "Party: {{ party_name }}"
		doc.validate()
		doc.contract_terms = None
		doc.validate()

	def test_get_contract_template_renders_terms(self):
		template = frappe.get_doc(
			{
				"doctype": "Contract Template",
				"title": "_Test Contract Template",
				"contract_terms": "Party: {{ party_name }}",
			}
		).insert()

		result = get_contract_template(template.name, {"party_name": "Acme"})
		self.assertEqual(result["contract_terms"], "Party: Acme")
		self.assertEqual(result["contract_template"].name, template.name)

	def test_get_contract_template_without_terms_returns_none(self):
		template = frappe.get_doc(
			{"doctype": "Contract Template", "title": "_Test Empty Contract Template"}
		).insert()

		result = get_contract_template(template.name, {})
		self.assertIsNone(result["contract_terms"])
