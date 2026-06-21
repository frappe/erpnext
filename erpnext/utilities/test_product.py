# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.controllers.item_variant import create_variant
from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.product import get_item_codes_by_attributes


class TestProduct(ERPNextTestSuite):
	def test_get_item_codes_by_attributes_is_case_insensitive(self):
		# get_item_codes_by_attributes matches Item Variant Attribute values. A raw equality is
		# case-sensitive on Postgres, so a differently-cased filter value would miss variants that
		# MariaDB (case-insensitive collation) matches. Lower() both sides keeps MariaDB unchanged and
		# makes Postgres match too.
		template = "_Test Variant Item"
		variant = create_variant(template, {"Test Size": "Small"})
		if not frappe.db.exists("Item", variant.name):
			variant.insert()
			self.addCleanup(frappe.delete_doc, "Item", variant.name, force=True)

		# stored attribute value is "Small"; query with a different case
		matches = get_item_codes_by_attributes({"Test Size": ["small"]}, template)
		self.assertIn(variant.name, matches)
