# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.accounts_controller import (
	_get_default_taxes_and_charges,
	_get_taxes_and_charges,
	get_default_taxes_and_charges,
	get_taxes_and_charges,
)
from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	make_company_fenced_user,
	make_fenced_user,
)

test_records = frappe.get_test_records("Sales Taxes and Charges Template")

TEMPLATE_DOCTYPE = "Sales Taxes and Charges Template"


class TestSalesTaxesandChargesTemplate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def get_template(self):
		return frappe.db.get_value(
			TEMPLATE_DOCTYPE, {"title": "_Test Sales Taxes and Charges Template", "company": "_Test Company"}
		)

	def make_default(self, template):
		company = frappe.db.get_value(TEMPLATE_DOCTYPE, template, "company")
		frappe.db.set_value(TEMPLATE_DOCTYPE, {"company": company}, "is_default", 0)
		frappe.db.set_value(TEMPLATE_DOCTYPE, template, "is_default", 1)

	def get_other_company_default(self):
		template = frappe.db.get_value(TEMPLATE_DOCTYPE, {"company": OTHER_COMPANY})
		if not template:
			account = frappe.db.get_value(
				"Account", {"company": OTHER_COMPANY, "is_group": 0, "account_type": "Tax"}
			)
			template = (
				frappe.get_doc(
					{
						"doctype": TEMPLATE_DOCTYPE,
						"title": "_Test Other Company Template",
						"company": OTHER_COMPANY,
						"taxes": [
							{
								"charge_type": "On Net Total",
								"account_head": account,
								"description": "VAT",
								"rate": 5,
							}
						],
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		self.make_default(template)
		return template

	def test_get_taxes_and_charges_checks_the_template(self):
		template = self.get_template()

		def taxes_kwargs(name):
			return {"master_doctype": TEMPLATE_DOCTYPE, "master_name": name}

		outside = make_company_fenced_user("taxes-outside@example.com", ["Sales User"], OTHER_COMPANY)
		with as_user(outside):
			assert_refused_for_names(self, get_taxes_and_charges, taxes_kwargs, [template])
		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			assert_refused(self, get_taxes_and_charges, **taxes_kwargs(template))
		inside = make_company_fenced_user("taxes-inside@example.com", ["Sales User"], "_Test Company")
		with as_user(inside):
			taxes = get_taxes_and_charges(TEMPLATE_DOCTYPE, template)
		self.assertEqual(taxes, _get_taxes_and_charges(TEMPLATE_DOCTYPE, template))
		self.assertEqual(len(taxes), len(frappe.get_doc(TEMPLATE_DOCTYPE, template).taxes))

	def test_get_default_taxes_and_charges_checks_the_default_template(self):
		template = self.get_template()
		self.make_default(template)

		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			assert_refused(self, get_default_taxes_and_charges, TEMPLATE_DOCTYPE, company="_Test Company")
		inside = make_company_fenced_user("taxes-inside@example.com", ["Sales User"], "_Test Company")
		with as_user(inside):
			default = get_default_taxes_and_charges(TEMPLATE_DOCTYPE, company="_Test Company")
		self.assertEqual(default["taxes_and_charges"], template)
		self.assertTrue(default["taxes"])

	def test_get_default_taxes_and_charges_checks_another_companys_default(self):
		template = self.get_other_company_default()
		self.assertEqual(
			_get_default_taxes_and_charges(TEMPLATE_DOCTYPE, company=OTHER_COMPANY)["taxes_and_charges"],
			template,
		)

		unfenced = make_fenced_user("taxes-unfenced@example.com", ["Projects User"])
		with as_user(unfenced):
			assert_refused(self, get_default_taxes_and_charges, TEMPLATE_DOCTYPE, company=OTHER_COMPANY)
		fenced = make_company_fenced_user("taxes-inside@example.com", ["Sales User"], "_Test Company")
		with as_user(fenced):
			assert_refused(self, get_default_taxes_and_charges, TEMPLATE_DOCTYPE, company=OTHER_COMPANY)

	def test_read_or_select_on_the_template_is_enough(self):
		template = self.get_template()
		expected = _get_taxes_and_charges(TEMPLATE_DOCTYPE, template)

		for email, role in (
			("taxes-read-only@example.com", "Sales User"),
			("taxes-sales-manager@example.com", "Sales Manager"),
			("taxes-accounts-user@example.com", "Accounts User"),
			("taxes-stock-user@example.com", "Stock User"),
			("taxes-purchase-manager@example.com", "Purchase Manager"),
			("taxes-purchase-user@example.com", "Purchase User"),
			("taxes-manufacturing-manager@example.com", "Manufacturing Manager"),
			("taxes-manufacturing-user@example.com", "Manufacturing User"),
		):
			user = make_fenced_user(email, [role])
			with as_user(user):
				self.assertEqual(get_taxes_and_charges(TEMPLATE_DOCTYPE, template), expected, role)

	def test_internal_callers_skip_the_template_check(self):
		template = self.get_template()
		self.make_default(template)

		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			self.assertTrue(_get_taxes_and_charges(TEMPLATE_DOCTYPE, template))
			self.assertEqual(
				_get_default_taxes_and_charges(TEMPLATE_DOCTYPE, company="_Test Company")[
					"taxes_and_charges"
				],
				template,
			)
