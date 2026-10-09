# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe

from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	make_company_fenced_user,
	make_fenced_user,
)
from erpnext.tests.utils import ERPNextTestSuite

TEMPLATE_DOCTYPE = "Sales Taxes and Charges Template"


class TestSalesTaxesandChargesTemplate(ERPNextTestSuite):
	def get_template(self):
		return frappe.db.get_value(
			TEMPLATE_DOCTYPE, {"title": "_Test Sales Taxes and Charges Template", "company": "_Test Company"}
		)

	def test_get_taxes_and_charges_checks_the_template(self):
		from erpnext.accounts.services.taxes import get_taxes_and_charges

		template = self.get_template()

		def taxes_kwargs(name):
			return {"master_doctype": TEMPLATE_DOCTYPE, "master_name": name}

		outside = make_company_fenced_user("taxes-fenced@example.com", ["Sales User"], OTHER_COMPANY)
		with as_user(outside):
			assert_refused_for_names(self, get_taxes_and_charges, taxes_kwargs, [template], type_gated=True)
		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			assert_refused(self, get_taxes_and_charges, **taxes_kwargs(template))
		inside = make_company_fenced_user("taxes-fenced@example.com", ["Sales User"], "_Test Company")
		with as_user(inside):
			taxes = get_taxes_and_charges(TEMPLATE_DOCTYPE, template)
		self.assertEqual(len(taxes), len(frappe.get_doc(TEMPLATE_DOCTYPE, template).taxes))

	def test_get_default_taxes_and_charges_checks_the_default_template(self):
		from erpnext.accounts.services.taxes import get_default_taxes_and_charges

		template = self.get_template()
		frappe.db.set_value(TEMPLATE_DOCTYPE, {"company": "_Test Company"}, "is_default", 0)
		frappe.db.set_value(TEMPLATE_DOCTYPE, template, "is_default", 1)

		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			assert_refused(self, get_default_taxes_and_charges, TEMPLATE_DOCTYPE, company="_Test Company")
		inside = make_company_fenced_user("taxes-fenced@example.com", ["Sales User"], "_Test Company")
		with as_user(inside):
			default = get_default_taxes_and_charges(TEMPLATE_DOCTYPE, company="_Test Company")
		self.assertEqual(default["taxes_and_charges"], template)
		self.assertTrue(default["taxes"])

	def test_internal_callers_skip_the_template_check(self):
		from erpnext.accounts.services.taxes import _get_default_taxes_and_charges, _get_taxes_and_charges

		template = self.get_template()
		frappe.db.set_value(TEMPLATE_DOCTYPE, {"company": "_Test Company"}, "is_default", 0)
		frappe.db.set_value(TEMPLATE_DOCTYPE, template, "is_default", 1)

		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			self.assertTrue(_get_taxes_and_charges(TEMPLATE_DOCTYPE, template))
			self.assertEqual(
				_get_default_taxes_and_charges(TEMPLATE_DOCTYPE, company="_Test Company")[
					"taxes_and_charges"
				],
				template,
			)

	def test_get_taxes_and_charges_allows_subcontracting_and_manufacturing_roles(self):
		from erpnext.accounts.services.taxes import get_taxes_and_charges

		template = self.get_template()
		expected = len(frappe.get_doc(TEMPLATE_DOCTYPE, template).taxes)

		for role in ("Purchase Manager", "Purchase User", "Manufacturing Manager", "Manufacturing User"):
			user = make_fenced_user(f"taxes-{frappe.scrub(role).replace('_', '-')}@example.com", [role])
			with as_user(user):
				self.assertEqual(len(get_taxes_and_charges(TEMPLATE_DOCTYPE, template)), expected, role)

		roleless = make_fenced_user("taxes-roleless@example.com", [])
		with as_user(roleless):
			assert_refused(self, get_taxes_and_charges, TEMPLATE_DOCTYPE, template)
