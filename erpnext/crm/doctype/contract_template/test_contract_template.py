# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.crm.doctype.contract_template.contract_template import get_contract_template
from erpnext.tests.utils import ERPNextTestSuite


class TestContractTemplate(ERPNextTestSuite):
	def test_single_line_terms_ending_in_a_file_extension_render_as_text(self):
		terms = "Standard terms apply, see https://example.com/terms.html"
		template = frappe.get_doc(
			{"doctype": "Contract Template", "title": "_Test Link Contract Template", "contract_terms": terms}
		).insert()

		self.assertEqual(get_contract_template(template.name, {})["contract_terms"], terms)

	def test_blank_contract_fields_render_empty(self):
		template = frappe.get_doc(
			{
				"doctype": "Contract Template",
				"title": "_Test Blank Fields Contract Template",
				"contract_terms": "From: {{ start_date }}, To: {{ end_date }}",
			}
		).insert()

		for doc in (
			{"doctype": "Contract", "start_date": "2026-10-03", "end_date": None},
			{"start_date": "2026-10-03"},
		):
			self.assertEqual(
				get_contract_template(template.name, doc)["contract_terms"], "From: 2026-10-03, To: "
			)
