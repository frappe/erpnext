# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.item import get_uom_conv_factor
from erpnext.tests.utils import ERPNextTestSuite


class TestUOMConversionFactor(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		self.category = "_Test UOM Conversion Factor"
		self.from_uom = "_Test UOM Conversion Factor From"
		self.to_uom = "_Test UOM Conversion Factor To"

		if not frappe.db.exists("UOM Category", self.category):
			frappe.get_doc({"doctype": "UOM Category", "category_name": self.category}).insert()

		for uom in (self.from_uom, self.to_uom):
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({"doctype": "UOM", "uom_name": uom, "category": self.category}).insert()

	def make_conversion_factor(self, from_uom=None, to_uom=None, value=1):
		return frappe.get_doc(
			{
				"doctype": "UOM Conversion Factor",
				"category": self.category,
				"from_uom": from_uom or self.from_uom,
				"to_uom": to_uom or self.to_uom,
				"value": value,
			}
		)

	def test_rejects_non_positive_value(self):
		for value in (0, -1):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				self.make_conversion_factor(value=value).insert()

	def test_ignores_legacy_non_positive_value(self):
		from_uom = "_Test Legacy UOM Conversion Factor From"
		to_uom = "_Test Legacy UOM Conversion Factor To"
		for uom in (from_uom, to_uom):
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({"doctype": "UOM", "uom_name": uom, "category": self.category}).insert()

		for value in (0, -1):
			with self.subTest(value=value):
				conversion_factor = self.make_conversion_factor(from_uom, to_uom, value)
				conversion_factor.db_insert()
				self.assertIsNone(get_uom_conv_factor(from_uom, to_uom))

	def test_rejects_self_conversion(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_conversion_factor(self.from_uom, self.from_uom).insert()

	def test_rejects_direct_and_inverse_duplicates(self):
		self.make_conversion_factor(value=10).insert()

		for from_uom, to_uom in ((self.from_uom, self.to_uom), (self.to_uom, self.from_uom)):
			with self.subTest(from_uom=from_uom, to_uom=to_uom), self.assertRaises(frappe.ValidationError):
				self.make_conversion_factor(from_uom, to_uom, 2).insert()
