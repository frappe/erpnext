# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.item import get_uom_conv_factor
from erpnext.tests.utils import ERPNextTestSuite


class TestUOMCategory(ERPNextTestSuite):
	def test_conversion_does_not_bridge_categories(self):
		for uom in ("_Test Bridge U1", "_Test Bridge U2", "_Test Bridge U3"):
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert()

		create_conversion("_Test Bridge Category A", "_Test Bridge U1", "_Test Bridge U2", 10)
		create_conversion("_Test Bridge Category B", "_Test Bridge U1", "_Test Bridge U3", 4)

		self.assertIsNone(get_uom_conv_factor("_Test Bridge U2", "_Test Bridge U3"))

		create_conversion("_Test Bridge Category A", "_Test Bridge U1", "_Test Bridge U3", 5)
		self.assertEqual(get_uom_conv_factor("_Test Bridge U2", "_Test Bridge U3"), 0.5)


def create_conversion(category, from_uom, to_uom, value):
	if not frappe.db.exists("UOM Category", category):
		frappe.get_doc({"doctype": "UOM Category", "category_name": category}).insert()

	frappe.get_doc(
		{
			"doctype": "UOM Conversion Factor",
			"category": category,
			"from_uom": from_uom,
			"to_uom": to_uom,
			"value": value,
		}
	).insert()
