# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from jinja2.sandbox import SandboxedEnvironment

from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import get_terms_and_conditions


class TestTermsAndConditions(UnitTestCase):
	def test_literal_terms_with_file_extensions(self):
		for extension in ("html", "txt", "md"):
			with self.subTest(extension=extension):
				terms = "Full terms for {{ customer }} at https://example.com/terms." + extension
				with (
					patch("frappe.get_cached_doc") as get_doc,
					patch(
						"erpnext.setup.doctype.terms_and_conditions.terms_and_conditions.get_jenv",
						return_value=SandboxedEnvironment(),
					),
				):
					get_doc.return_value.terms = terms
					self.assertEqual(
						get_terms_and_conditions("Test", {"customer": "Acme"}),
						"Full terms for Acme at https://example.com/terms." + extension,
					)
