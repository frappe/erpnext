# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestAssetShiftFactor(ERPNextTestSuite):
	def test_default_factor_can_be_edited_but_not_duplicated(self):
		frappe.db.delete("Asset Shift Factor")
		default = frappe.get_doc(
			{"doctype": "Asset Shift Factor", "shift_name": "Single", "shift_factor": 1, "default": 1}
		).insert()
		default.shift_factor = 1.2
		default.save()

		double = frappe.get_doc(
			{"doctype": "Asset Shift Factor", "shift_name": "Double", "shift_factor": 1.5, "default": 1}
		)
		self.assertRaises(frappe.ValidationError, double.insert)

	def test_shift_factor_must_be_positive(self):
		frappe.db.delete("Asset Shift Factor")
		for factor in (0, -1, "0", None):
			shift = frappe.get_doc(
				{"doctype": "Asset Shift Factor", "shift_name": "Zero", "shift_factor": factor}
			)
			self.assertRaisesRegex(frappe.ValidationError, "must be greater than zero", shift.insert)

		shift = frappe.get_doc(
			{"doctype": "Asset Shift Factor", "shift_name": "Double", "shift_factor": "1.5"}
		)
		shift.insert()
		self.assertEqual(frappe.db.get_value("Asset Shift Factor", shift.name, "shift_factor"), 1.5)
