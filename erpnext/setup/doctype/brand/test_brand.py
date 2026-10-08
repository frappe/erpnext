# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestBrand(ERPNextTestSuite):
	def test_default_company_and_inventory_account(self):
		brand = frappe.get_doc({"doctype": "Brand", "brand": "Test Brand Defaults"})
		brand.append(
			"brand_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
		)
		brand.append("brand_defaults", {"company": "_Test Company"})
		with self.assertRaisesRegex(frappe.ValidationError, "multiple Item Defaults"):
			brand.validate()

		brand.brand_defaults.pop()
		brand.brand_defaults[0].company = "_Test Company 1"
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
			brand.validate()

		brand.brand_defaults[0].company = "_Test Company"
		brand.brand_defaults[0].default_inventory_account = "_Test Account Sales - _TC"
		with self.assertRaisesRegex(frappe.ValidationError, "must be a Stock account"):
			brand.validate()

		brand.brand_defaults[0].default_inventory_account = None
		brand.brand_defaults[0].purchase_expense_account = "_Test Account Sales - _TC"
		brand.brand_defaults[0].company = "_Test Company 1"
		brand.brand_defaults[0].default_warehouse = None
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company"):
			brand.validate()
