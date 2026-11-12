# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestItemVariantSettings(FrappeTestCase):
	def test_unsafe_fields_cannot_be_copied_to_variants(self):
		for fieldname in ("attributes", "has_variants", "variant_of"):
			settings = frappe.get_doc("Item Variant Settings")
			settings.append("fields", {"field_name": fieldname})
			self.assertRaises(frappe.ValidationError, settings.save)
