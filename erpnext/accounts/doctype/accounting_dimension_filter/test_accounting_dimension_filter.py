# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.model.meta import Meta

from erpnext.accounts.doctype.accounting_dimension_filter.accounting_dimension_filter import (
	get_dimension_filter_map,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.exceptions import InvalidAccountDimensionError, MandatoryAccountDimensionError
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountingDimensionFilter(ERPNextTestSuite):
	def setUp(self):
		create_accounting_dimension_filter()
		self.invoice_list = []

	def test_allowed_dimension_validation(self):
		si = create_sales_invoice(do_not_save=1)
		si.items[0].cost_center = "Main - _TC"
		si.department = "Accounts - _TC"
		si.location = "Block 1"
		si.save()

		self.assertRaises(InvalidAccountDimensionError, si.submit)
		self.invoice_list.append(si)

	def test_mandatory_dimension_validation(self):
		si = create_sales_invoice(do_not_save=1)
		si.department = ""
		si.location = "Block 1"

		# Test with no department for Sales Account
		si.items[0].department = ""
		si.items[0].cost_center = "_Test Cost Center 2 - _TC"
		si.save()

		self.assertRaises(MandatoryAccountDimensionError, si.submit)
		self.invoice_list.append(si)

	def test_mandatory_dimension_message_uses_translated_label(self):
		si = create_sales_invoice(do_not_save=1)
		si.department = ""
		si.location = "Block 1"
		si.items[0].department = ""
		si.items[0].cost_center = "_Test Cost Center 2 - _TC"
		si.save()
		self.invoice_list.append(si)

		with patch.object(Meta, "get_translated_label", return_value="Abteilung") as get_label:
			with self.assertRaises(MandatoryAccountDimensionError) as raised:
				si.submit()

		get_label.assert_any_call("department")
		self.assertIn("Abteilung", str(raised.exception))

	def test_invalid_dimension_message_uses_translated_label(self):
		si = create_sales_invoice(do_not_save=1)
		si.items[0].cost_center = "Main - _TC"
		si.department = "Accounts - _TC"
		si.location = "Block 1"
		si.save()
		self.invoice_list.append(si)

		with patch.object(Meta, "get_translated_label", return_value="Kostenstelle") as get_label:
			with self.assertRaises(InvalidAccountDimensionError) as raised:
				si.submit()

		get_label.assert_any_call("cost_center")
		self.assertIn("Kostenstelle", str(raised.exception))

	def test_message_names_dimension_whose_field_is_missing(self):
		# a filter outlives its deleted dimension: no field on GL Entry, the fieldname is all that is left
		frappe.get_doc(
			{
				"doctype": "Accounting Dimension Filter",
				"accounting_dimension": "Test Removed Dimension",
				"allow_or_restrict": "Restrict",
				"apply_restriction_on_values": 0,
				"company": "_Test Company",
				"accounts": [{"applicable_on_account": "Sales - _TC", "is_mandatory": 1}],
			}
		).insert()

		si = create_sales_invoice(do_not_save=1)
		si.department = "Accounts - _TC"
		si.location = "Block 1"
		si.items[0].department = "Accounts - _TC"
		si.items[0].cost_center = "_Test Cost Center 2 - _TC"
		si.save()
		self.invoice_list.append(si)

		with self.assertRaises(MandatoryAccountDimensionError) as raised:
			si.submit()

		self.assertIn("Test Removed Dimension", str(raised.exception))
		self.assertNotIn("No Label", str(raised.exception))

	def test_group_account_is_refused(self):
		doc = frappe.get_doc(
			{
				"doctype": "Accounting Dimension Filter",
				"accounting_dimension": "Project",
				"allow_or_restrict": "Restrict",
				"apply_restriction_on_values": 0,
				"company": "_Test Company",
				"accounts": [{"applicable_on_account": "Indirect Expenses - _TC", "is_mandatory": 1}],
			}
		)

		self.assertRaisesRegex(frappe.ValidationError, "is a group account", doc.insert)

	def test_filter_of_disabled_dimension_is_not_enforced(self):
		self.assertIn(("department", "Sales - _TC"), get_dimension_filter_map())

		frappe.db.set_value("Accounting Dimension", {"document_type": "Department"}, "disabled", 1)

		dimension_filter_map = get_dimension_filter_map()
		self.assertNotIn(("department", "Sales - _TC"), dimension_filter_map)
		self.assertIn(("cost_center", "Sales - _TC"), dimension_filter_map)

	def test_disabled_filter_does_not_block_a_new_filter(self):
		disable_dimension_filter()

		frappe.get_doc(
			{
				"doctype": "Accounting Dimension Filter",
				"accounting_dimension": "Department",
				"allow_or_restrict": "Restrict",
				"apply_restriction_on_values": 0,
				"company": "_Test Company",
				"accounts": [{"applicable_on_account": "Sales - _TC", "is_mandatory": 1}],
			}
		).insert()

		# re-enabling the old filter now conflicts with the new one
		doc = frappe.get_doc(
			"Accounting Dimension Filter", {"accounting_dimension": "Department", "disabled": 1}
		)
		doc.disabled = 0
		self.assertRaisesRegex(frappe.ValidationError, "already applied", doc.save)


def create_accounting_dimension_filter():
	if not frappe.db.get_value("Accounting Dimension Filter", {"accounting_dimension": "Cost Center"}):
		frappe.get_doc(
			{
				"doctype": "Accounting Dimension Filter",
				"accounting_dimension": "Cost Center",
				"allow_or_restrict": "Allow",
				"company": "_Test Company",
				"apply_restriction_on_values": 1,
				"accounts": [
					{
						"applicable_on_account": "Sales - _TC",
					}
				],
				"dimensions": [
					{"accounting_dimension": "Cost Center", "dimension_value": "_Test Cost Center 2 - _TC"}
				],
			}
		).insert()
	else:
		doc = frappe.get_doc("Accounting Dimension Filter", {"accounting_dimension": "Cost Center"})
		doc.disabled = 0
		doc.save()

	if not frappe.db.get_value("Accounting Dimension Filter", {"accounting_dimension": "Department"}):
		frappe.get_doc(
			{
				"doctype": "Accounting Dimension Filter",
				"accounting_dimension": "Department",
				"allow_or_restrict": "Allow",
				"apply_restriction_on_values": 1,
				"company": "_Test Company",
				"accounts": [{"applicable_on_account": "Sales - _TC", "is_mandatory": 1}],
				"dimensions": [{"accounting_dimension": "Department", "dimension_value": "Accounts - _TC"}],
			}
		).insert()
	else:
		doc = frappe.get_doc("Accounting Dimension Filter", {"accounting_dimension": "Department"})
		doc.disabled = 0
		doc.save()


def disable_dimension_filter():
	doc = frappe.get_doc("Accounting Dimension Filter", {"accounting_dimension": "Cost Center"})
	doc.disabled = 1
	doc.save()

	doc = frappe.get_doc("Accounting Dimension Filter", {"accounting_dimension": "Department"})
	doc.disabled = 1
	doc.save()
