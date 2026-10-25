# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer import (
	build_forest,
	unset_existing_data,
	validate_columns,
	validate_company,
	validate_missing_roots,
)
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite

# columns: account_name, parent_account, account_number, parent_account_number,
#          is_group, account_type, root_type, account_currency
ROOT = ["Assets", "Assets", "", "", 1, "", "Asset", "INR"]
CHILD = ["Cash", "Assets", "", "", 0, "Cash", "Asset", "INR"]


class TestChartofAccountsImporter(ERPNextTestSuite):
	"""Cover chart validation and replacement without breaking existing links."""

	def test_validate_columns_rejects_blank_file(self):
		self.assertRaises(frappe.ValidationError, validate_columns, [])

	def test_validate_columns_requires_eight_columns(self):
		self.assertRaises(frappe.ValidationError, validate_columns, [["a", "b", "c"]])
		# the standard template width passes
		validate_columns([ROOT])

	def test_build_forest_nests_child_under_parent(self):
		forest = build_forest([ROOT, CHILD])
		self.assertIn("Assets", forest)
		self.assertIn("Cash", forest["Assets"])

	def test_build_forest_rejects_unknown_parent(self):
		orphan = ["Cash", "Missing Parent", "", "", 0, "Cash", "Asset", "INR"]
		self.assertRaises(frappe.ValidationError, build_forest, [orphan])

	def test_build_forest_requires_account_name(self):
		nameless = ["", "Assets", "", "", 0, "Cash", "Asset", "INR"]
		self.assertRaises(frappe.ValidationError, build_forest, [ROOT, nameless])

	def test_validate_missing_roots_requires_all_root_types(self):
		present = ("Asset", "Liability", "Expense", "Income")  # Equity missing
		self.assertRaises(
			frappe.ValidationError,
			validate_missing_roots,
			[{"root_type": rt} for rt in present],
		)
		# all five root types present -> no error
		validate_missing_roots(
			[{"root_type": rt} for rt in ("Asset", "Liability", "Expense", "Income", "Equity")]
		)

	def test_unset_existing_data_as_accounts_manager(self):
		company = frappe.get_doc(
			doctype="Company",
			company_name="_Test COA Import",
			abbr="TCI",
			country="United States",
			default_currency="USD",
			chart_of_accounts="Standard",
		).insert()
		# Regional item tax templates would independently block account replacement.
		for name in frappe.get_all("Item Tax Template", filters={"company": company.name}, pluck="name"):
			frappe.delete_doc("Item Tax Template", name)

		templates = []
		for doctype in ("Sales Taxes and Charges Template", "Purchase Taxes and Charges Template"):
			templates.append(
				frappe.get_doc(
					doctype=doctype,
					title="_Test Import Tax",
					company=company.name,
					taxes=[
						{
							"charge_type": "On Net Total",
							"account_head": company.default_expense_account,
							"description": "Import tax",
							"rate": 5,
						}
					],
				).insert()
			)
		user = make_fenced_user("coa-import-manager@example.com", ["Accounts Manager"])

		with self.set_user(user):
			self.assertFalse(frappe.has_permission("Purchase Taxes and Charges Template", "delete"))
			self.assertTrue(frappe.has_permission("Company", "write", company.name))
			validate_company(company.name)
			unset_existing_data(company.name)

		self.assertFalse(frappe.db.exists("Account", {"company": company.name}))
		for template in templates:
			self.assertFalse(frappe.db.exists(template.doctype, template.name))
			self.assertFalse(frappe.db.exists(template.taxes[0].doctype, template.taxes[0].name))
