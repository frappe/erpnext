from unittest import mock
from unittest.mock import patch

import frappe
from frappe.utils import flt

from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


def resolve_on_gross(calc, item, tax):
	# base = gross printed line amount
	return flt(item.amount)


def resolve_on_mrp(calc, item, tax):
	# base = MRP, not net
	return flt(item.price_list_rate) * flt(item.qty)


class TestTaxesAndTotals(ERPNextTestSuite):
	def test_regional_round_off_accounts(self):
		"""
		Regional overrides cannot extend the list in-place — the return
		value must be assigned back to frappe.flags.round_off_applicable_accounts.
		"""
		test_account = "_Test Round Off Account"

		def mock_regional(company, account_list: list, doc=None) -> list:
			# Simulates a regional override
			account_list.extend([test_account])
			return account_list

		so = make_sales_order(do_not_save=True)

		with patch(
			"erpnext.controllers.taxes_and_totals.get_regional_round_off_accounts",
			mock_regional,
		):
			calculate_taxes_and_totals(so)

		self.assertIn(test_account, frappe.flags.round_off_applicable_accounts)

	def test_exclusive_custom_charge_on_resolved_base(self):
		"""Added (exclusive) custom charge_type whose base is resolved by the
		`erpnext_taxable_base_resolvers` hook. IPI 10% on the gross product value 1000
		-> tax 100, net 1000, grand 1100."""
		so = make_sales_order(do_not_save=True)
		so.items = []
		so.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 1000,
				"price_list_rate": 1000,
				"warehouse": "_Test Warehouse - _TC",
			},
		)
		so.set("taxes", [])
		so.append(
			"taxes",
			{
				"charge_type": "On Gross Value",
				"account_head": "_Test Account Excise Duty - _TC",
				"description": "IPI 10% on gross product value",
				"rate": 10,
				"cost_center": "_Test Cost Center - _TC",
			},
		)

		real_get_hooks = frappe.get_hooks

		def fake_get_hooks(hook=None, *args, **kwargs):
			if hook == "erpnext_taxable_base_resolvers":
				return {
					"On Gross Value": ["erpnext.controllers.tests.test_taxes_and_totals.resolve_on_gross"]
				}
			return real_get_hooks(hook, *args, **kwargs)

		with mock.patch("frappe.get_hooks", side_effect=fake_get_hooks):
			calculate_taxes_and_totals(so)

		self.assertEqual(so.net_total, 1000.0)
		self.assertEqual(so.taxes[0].tax_amount, 100.0)
		self.assertEqual(so.grand_total, 1100.0)

	def test_inclusive_custom_charge_on_resolved_base(self):
		"""Inclusive custom charge on a resolved base backs out non-compounding
		(tax = rate x resolved base) — a resolved base is fixed, so it never
		compounds. MRP 1200, printed 1000, rate 10%: tax 120, net 880."""
		so = make_sales_order(do_not_save=True)
		so.items = []
		so.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 1000,
				"price_list_rate": 1200,
				"warehouse": "_Test Warehouse - _TC",
			},
		)
		so.set("taxes", [])
		so.append(
			"taxes",
			{
				"charge_type": "On MRP",
				"account_head": "_Test Account VAT - _TC",
				"description": "Tax 10% on MRP, inclusive",
				"rate": 10,
				"included_in_print_rate": 1,
				"cost_center": "_Test Cost Center - _TC",
			},
		)

		real_get_hooks = frappe.get_hooks

		def fake_get_hooks(hook=None, *args, **kwargs):
			if hook == "erpnext_taxable_base_resolvers":
				return {"On MRP": ["erpnext.controllers.tests.test_taxes_and_totals.resolve_on_mrp"]}
			return real_get_hooks(hook, *args, **kwargs)

		with mock.patch("frappe.get_hooks", side_effect=fake_get_hooks):
			calculate_taxes_and_totals(so)

		self.assertEqual(so.taxes[0].tax_amount, 120.0)
		self.assertEqual(so.net_total, 880.0)
		self.assertEqual(so.grand_total, 1000.0)

	def test_base_rounded_total_without_transaction_rounding(self):
		"""Rounding the USD total changes nothing, so the base totals must agree too."""
		so = make_sales_order(do_not_save=True)
		so.currency = "USD"
		so.conversion_rate = 89.7
		so.set("taxes", [])
		so.items[0].qty = 15
		so.append("items", so.items[0].as_dict() | {"name": None, "qty": 155})
		for item in so.items:
			item.rate = item.price_list_rate = 99.07
			item.discount_percentage = item.discount_amount = 0

		calculate_taxes_and_totals(so)

		self.assertEqual(so.grand_total, 16841.9)
		self.assertEqual(so.rounding_adjustment, 0)
		self.assertEqual(so.base_grand_total, 1510718.42)
		self.assertEqual(so.base_rounding_adjustment, 0)
		self.assertEqual(so.base_rounded_total, 1510718.42)

	def test_base_rounded_total_with_transaction_rounding(self):
		"""JPY rounds to whole units: the base rounded total is the base total plus the base adjustment."""
		so = make_sales_order(do_not_save=True)
		so.currency = "JPY"
		so.conversion_rate = 0.567
		so.set("taxes", [])
		so.items[0].qty = 1
		so.items[0].rate = so.items[0].price_list_rate = 1701.4
		so.items[0].discount_percentage = so.items[0].discount_amount = 0

		calculate_taxes_and_totals(so)

		self.assertEqual(so.rounded_total, 1701)
		self.assertEqual(so.rounding_adjustment, -0.4)
		self.assertEqual(so.base_grand_total, 964.69)
		self.assertEqual(so.base_rounding_adjustment, -0.23)
		# 1701 * 0.567 rounds to 964.47, which would not match the base totals
		self.assertEqual(so.base_rounded_total, 964.46)

	def test_disabling_rounded_total_resets_base_fields(self):
		"""Disabling rounded total should also clear base rounded values."""
		so = make_sales_order(do_not_save=True)
		so.items[0].qty = 1
		so.items[0].rate = 1000.25
		so.items[0].price_list_rate = 1000.25
		so.items[0].discount_percentage = 0
		so.items[0].discount_amount = 0
		so.set("taxes", [])

		so.disable_rounded_total = 0
		calculate_taxes_and_totals(so)

		self.assertEqual(so.grand_total, 1000.25)
		self.assertEqual(so.rounded_total, 1000.0)
		self.assertEqual(so.rounding_adjustment, -0.25)
		self.assertEqual(so.base_grand_total, 1000.25)
		self.assertEqual(so.base_rounded_total, 1000.0)
		self.assertEqual(so.base_rounding_adjustment, -0.25)

		# User toggles disable_rounded_total after values are already set.
		so.disable_rounded_total = 1

		calculate_taxes_and_totals(so)

		self.assertEqual(so.rounded_total, 0)
		self.assertEqual(so.rounding_adjustment, 0)
		self.assertEqual(so.base_rounded_total, 0)
		self.assertEqual(so.base_rounding_adjustment, 0)
