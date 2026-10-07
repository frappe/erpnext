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
