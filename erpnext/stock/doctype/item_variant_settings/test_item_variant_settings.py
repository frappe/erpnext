# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.controllers.item_variant import create_variant
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestItemVariantSettings(ERPNextTestSuite):
	def make_template_with_variant(self, variant_uom):
		template = make_item(
			"_Test Variant UOM Template",
			{
				"is_stock_item": 1,
				"has_variants": 1,
				"stock_uom": "Nos",
				"attributes": [{"attribute": "Test Size"}],
			},
		)

		variant = create_variant(template.name, {"Test Size": "Small"})
		variant.stock_uom = variant_uom
		variant.set("uoms", [])
		variant.insert()
		return template, variant

	@ERPNextTestSuite.change_settings("Item Variant Settings", {"allow_different_uom": 1})
	def test_template_save_keeps_variant_uom_when_different_uom_allowed(self):
		template, variant = self.make_template_with_variant("Kg")
		make_stock_entry(item_code=variant.name, target="_Test Warehouse - _TC", qty=3, rate=100)

		template.reload()
		template.description = "Updated template description"
		template.save()

		variant.reload()
		self.assertEqual(variant.stock_uom, "Kg")
		self.assertEqual([row.uom for row in variant.uoms], ["Kg"])

	@ERPNextTestSuite.change_settings("Item Variant Settings", {"allow_different_uom": 1})
	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_uom_with_conversion_rate_defined_in_item": 1})
	def test_template_save_keeps_variant_default_uoms_when_different_uom_allowed(self):
		self.copy_fields_to_variants("sales_uom", "purchase_uom")
		template, variant = self.make_template_with_variant("Kg")
		variant.reload()
		variant.sales_uom = variant.purchase_uom = "Kg"
		variant.save()

		template.reload()
		template.sales_uom = template.purchase_uom = "Nos"
		template.save()

		variant.reload()
		self.assertEqual(variant.sales_uom, "Kg")
		self.assertEqual(variant.purchase_uom, "Kg")

	def copy_fields_to_variants(self, *fieldnames):
		settings = frappe.get_doc("Item Variant Settings")
		existing = [row.field_name for row in settings.fields]
		for fieldname in fieldnames:
			if fieldname not in existing:
				settings.append("fields", {"field_name": fieldname})

		settings.save()
		self.addCleanup(self.restore_variant_fields, existing)

	def restore_variant_fields(self, fieldnames):
		settings = frappe.get_doc("Item Variant Settings")
		settings.set("fields", [{"field_name": fieldname} for fieldname in fieldnames])
		settings.save()

	def test_unsafe_fields_cannot_be_copied_to_variants(self):
		for fieldname in ("attributes", "has_variants", "variant_of"):
			settings = frappe.get_doc("Item Variant Settings")
			settings.append("fields", {"field_name": fieldname})
			self.assertRaises(frappe.ValidationError, settings.save)
