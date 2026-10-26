# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer import (
	unset_existing_data,
	validate_company,
)
from erpnext.tests.permission_test_utils import make_fenced_user


class TestChartofAccountsImporter(FrappeTestCase):
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
