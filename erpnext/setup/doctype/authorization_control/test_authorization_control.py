# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestAuthorizationControl(ERPNextTestSuite):
	def test_foreign_currency_additional_discount_uses_base_amount(self):
		frappe.get_doc(
			{
				"doctype": "Authorization Rule",
				"transaction": "Sales Order",
				"based_on": "Average Discount",
				"company": "_Test Company",
				"value": 10,
				"approving_user": "Administrator",
			}
		).insert()
		order = frappe._dict(
			doctype="Sales Order",
			customer_name="_Test Customer",
			items=[frappe._dict(base_price_list_rate=8300, base_rate=8300, qty=1)],
			discount_amount=30,
			base_discount_amount=2490,
		)
		with self.set_user("Guest"):
			with self.assertRaises(frappe.ValidationError):
				frappe.get_cached_doc("Authorization Control").validate_approving_authority(
					"Sales Order", "_Test Company", 5810, order
				)

	def test_zero_rate_items_count_toward_average_discount(self):
		frappe.get_doc(
			{
				"doctype": "Authorization Rule",
				"transaction": "Sales Order",
				"based_on": "Average Discount",
				"company": "_Test Company",
				"value": 10,
				"approving_user": "Administrator",
			}
		).insert()
		order = frappe._dict(
			doctype="Sales Order",
			customer_name="_Test Customer",
			items=[
				frappe._dict(base_price_list_rate=4200, base_rate=4200, qty=1),
				frappe._dict(base_price_list_rate=4200, base_rate=0, qty=1),
			],
			discount_amount=0,
		)
		with self.set_user("Guest"):
			with self.assertRaises(frappe.ValidationError):
				frappe.get_cached_doc("Authorization Control").validate_approving_authority(
					"Sales Order", "_Test Company", 4200, order
				)

	def test_update_items_checks_discounts_on_updated_parent(self):
		from erpnext.accounts.services.child_item_update import ChildItemUpdater

		updater = object.__new__(ChildItemUpdater)
		updater.parent = MagicMock(doctype="Sales Order", company="_Test Company", base_grand_total=500)
		updater.parent_doctype = "Sales Order"
		with patch("erpnext.accounts.services.child_item_update.frappe.get_cached_doc") as get_control:
			get_control.return_value.validate_approving_authority.side_effect = frappe.ValidationError(
				"discount exceeds limit"
			)
			with self.assertRaises(frappe.ValidationError):
				updater._post_update(False, False, False)
			get_control.return_value.validate_approving_authority.assert_called_once_with(
				"Sales Order", "_Test Company", 500, updater.parent
			)

	def test_auto_repeat_invoice_still_checks_approval(self):
		invoice = frappe.get_doc({"doctype": "Sales Invoice", "auto_repeat": "OTHER-REPEAT"})
		with (
			patch("erpnext.accounts.doctype.sales_invoice.sales_invoice.POSService"),
			patch(
				"erpnext.accounts.doctype.sales_invoice.sales_invoice.frappe.get_cached_doc"
			) as get_control,
		):
			get_control.return_value.validate_approving_authority.side_effect = frappe.ValidationError(
				"approval required"
			)
			with self.assertRaises(frappe.ValidationError):
				invoice.on_submit()
			get_control.return_value.validate_approving_authority.assert_called_once_with(
				"Sales Invoice", invoice.company, invoice.base_grand_total, invoice
			)

	def test_validate_approving_authority_raises_when_over_limit(self):
		# Exercises validate_approving_authority -> the based_on query-builder lookups and the
		# coalesce()-based rule lookups (formerly ifnull, which is invalid on Postgres).
		if not frappe.db.exists("Role", "_Test Approver Role"):
			frappe.get_doc({"doctype": "Role", "role_name": "_Test Approver Role"}).insert()

		# Run as a non-admin user without the approving role; Administrator implicitly holds every
		# role, so the not-authorized branch would never fire as Administrator.
		user = "_test_auth_control_user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Auth Control",
					"send_welcome_email": 0,
					"roles": [{"role": "Sales User"}],
				}
			).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Authorization Rule",
				"transaction": "Sales Order",
				"based_on": "Grand Total",
				"company": "_Test Company",
				"value": 1000,
				"approving_role": "_Test Approver Role",
			}
		).insert()

		controller = frappe.get_cached_doc("Authorization Control")
		# User lacks _Test Approver Role and the total exceeds the rule value -> not authorized.
		with self.set_user(user):
			self.assertRaises(
				frappe.ValidationError,
				controller.validate_approving_authority,
				"Sales Order",
				"_Test Company",
				5000,
			)

	def test_get_value_based_rule_runs(self):
		# Exercises the four query-builder lookups (incl. the Employee designation subquery) added in
		# get_value_based_rule; with no matching rule they must run and return empty on both engines.
		controller = frappe.get_cached_doc("Authorization Control")
		result = controller.get_value_based_rule("Expense Claim", "_NONEXISTENT-EMP", 100, "_Test Company")
		self.assertEqual(list(result), [])
