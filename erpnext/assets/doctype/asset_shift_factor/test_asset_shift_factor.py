# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.assets.doctype.asset.test_asset import create_asset
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

	def test_shift_based_depreciation_needs_a_positive_default_factor(self):
		for factor in (0, -1):
			shift = frappe.get_doc(
				{"doctype": "Asset Shift Factor", "shift_name": "Zero", "shift_factor": factor}
			)
			self.assertRaises(frappe.ValidationError, shift.insert)

		frappe.db.delete("Asset Shift Factor")
		frappe.clear_document_cache("Asset Shift Factor")
		self.assertRaises(
			frappe.ValidationError,
			create_asset,
			calculate_depreciation=1,
			available_for_use_date="2023-01-01",
			purchase_date="2023-01-01",
			depreciation_start_date="2023-01-31",
			total_number_of_depreciations=12,
			frequency_of_depreciation=1,
			shift_based=1,
		)
