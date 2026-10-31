from unittest import mock
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item


def resolve_on_gross(calc, item, tax):
	# base = gross printed line amount
	return flt(item.amount)


def resolve_on_mrp(calc, item, tax):
	# base = MRP, not net
	return flt(item.price_list_rate) * flt(item.qty)


class TestTaxesAndTotals(FrappeTestCase):
	def test_remove_pricing_discounts_on_sales_and_purchase(self):
		item = make_item("_Test Shared Discount Item", {"is_stock_item": 0})
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item.name,
				"price_list": "_Test Price List",
				"price_list_rate": 100,
			}
		).insert()
		rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Shared Discount",
				"company": "_Test Company",
				"price_or_product_discount": "Price",
				"apply_on": "Item Code",
				"items": [{"item_code": item.name}],
				"selling": 1,
				"buying": 1,
				"currency": "INR",
				"rate_or_discount": "Discount Amount",
				"discount_amount": 20,
			}
		).insert()
		for make_order in (make_sales_order, create_purchase_order):
			with self.subTest(make_order=make_order.__name__):
				order = make_order(item_code=item.name, qty=1, do_not_save=True)
				order.set(
					"selling_price_list" if order.doctype == "Sales Order" else "buying_price_list",
					"_Test Price List",
				)
				order.insert()
				self.assertEqual(order.items[0].rate, 80)
				self.assertEqual(frappe.parse_json(order.items[0].pricing_rules), [rule.name])
				order.ignore_pricing_rule = 1
				order.save()
				self.assertEqual(order.items[0].rate, 100)
				self.assertEqual(order.items[0].discount_percentage, 0)
				self.assertEqual(order.items[0].discount_amount, 0)
				self.assertFalse(order.items[0].pricing_rules)

				frappe.db.set_single_value(
					"Selling Settings" if order.doctype == "Sales Order" else "Buying Settings",
					"allow_multiple_items",
					1,
				)
				rule.price_or_product_discount = "Product"
				rule.same_item = 1
				rule.free_qty = 1
				rule.save()
				order.ignore_pricing_rule = 0
				order.save()
				self.assertEqual([row.pricing_rules for row in order.items if row.is_free_item], [rule.name])
				order.append("items", {"item_code": item.name, "qty": 2, "rate": 0, "is_free_item": 1})
				replacement = frappe.copy_doc(rule)
				replacement.same_item = 0
				replacement.free_item = "_Test Item"
				replacement.insert()
				rule.disable = 1
				rule.save()
				order.set_missing_item_details()
				order.save()
				self.assertEqual(
					[row.pricing_rules for row in order.items if row.is_free_item and row.pricing_rules],
					[replacement.name],
				)
				replacement.dont_enforce_free_item_qty = 1
				replacement.save()
				order.ignore_pricing_rule = 1
				order.save()
				self.assertEqual(sum(row.is_free_item for row in order.items), 2)
				order.ignore_pricing_rule = 0
				order.save()
				replacement.dont_enforce_free_item_qty = 0
				replacement.save()
				order.ignore_pricing_rule = 1
				order.save()
				self.assertEqual(
					[(row.item_code, row.qty) for row in order.items if row.is_free_item], [(item.name, 2)]
				)
				replacement.disable = 1
				replacement.save()
				rule.disable = 0
				rule.price_or_product_discount = "Price"
				rule.save()

	@ERPNextTestSuite.change_settings("System Settings", {"currency_precision": 2})
	def test_inclusive_rounding_with_tax_groups_and_alternative_items(self):
		template = frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": "_Test Inclusive Rounding",
				"company": "_Test Company",
				"taxes": [{"tax_type": "_Test Account Service Tax - _TC", "tax_rate": 10}],
			}
		).insert()
		quotation = frappe.get_doc(
			{
				"doctype": "Quotation",
				"company": "_Test Company",
				"currency": "INR",
				"conversion_rate": 1,
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 379,
						"is_alternative": alternative,
						"item_tax_template": template.name if rate == 10 else None,
					}
					for rate, alternative in [(21, 0), (21, 1), (10, 0), (21, 0), (10, 1), (10, 0), (21, 1)]
				],
				"taxes": [
					{
						"charge_type": "On Net Total",
						"account_head": "_Test Account Service Tax - _TC",
						"rate": 21,
						"included_in_print_rate": 1,
					}
				],
			}
		)
		for row_wise, expected in (
			(0, [313.22, 313.22, 344.55, 313.23, 344.55, 344.54, 313.22]),
			(1, [313.22, 313.22, 344.55, 313.22, 344.55, 344.55, 313.22]),
		):
			with (
				self.subTest(round_row_wise_tax=row_wise),
				self.change_settings("Accounts Settings", round_row_wise_tax=row_wise),
			):
				calculate_taxes_and_totals(quotation)
				for field in ("net_amount", "net_rate", "base_net_amount", "base_net_rate"):
					self.assertEqual([item.get(field) for item in quotation.items], expected)
				self.assertEqual(quotation.net_total, 1315.54)
				self.assertEqual(quotation.taxes[0].tax_amount, 200.46)
				self.assertEqual(quotation.taxes[0].total, 1516)
				self.assertEqual(quotation.grand_total, 1516)

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

	def test_tax_net_amount_with_not_applicable_item_tax(self):
		"""Each tax row records only the net of the items it actually applies to.

		Two items of 100 each, one per template. Template A applies VAT 7 and
		marks VAT 19 not applicable, template B does the reverse. Both tax rows
		must report a net_amount of 100, not the full net total of 200.
		"""
		vat_7 = "_Test Account VAT - _TC"
		vat_19 = "_Test Account Service Tax - _TC"

		templates = {}
		for title, rows in {
			"_Test NA Template A": [(vat_7, 7, 0), (vat_19, 0, 1)],
			"_Test NA Template B": [(vat_7, 0, 1), (vat_19, 19, 0)],
		}.items():
			doc = frappe.new_doc("Item Tax Template")
			doc.title = title
			doc.company = "_Test Company"
			for tax_type, tax_rate, not_applicable in rows:
				doc.append(
					"taxes",
					{"tax_type": tax_type, "tax_rate": tax_rate, "not_applicable": not_applicable},
				)
			templates[title] = doc.insert().name

		so = make_sales_order(do_not_save=True)
		so.items = []
		for title in templates:
			so.append(
				"items",
				{
					"item_code": "_Test Item",
					"qty": 1,
					"rate": 100,
					"warehouse": "_Test Warehouse - _TC",
					"item_tax_template": templates[title],
				},
			)

		so.set("taxes", [])
		for account_head in (vat_7, vat_19):
			so.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": account_head,
					"description": account_head,
					"rate": 0,
					"cost_center": "_Test Cost Center - _TC",
				},
			)

		so.save()

		self.assertEqual(so.net_total, 200.0)
		self.assertEqual(so.taxes[0].net_amount, 100.0)
		self.assertEqual(so.taxes[0].tax_amount, 7.0)
		self.assertEqual(so.taxes[1].net_amount, 100.0)
		self.assertEqual(so.taxes[1].tax_amount, 19.0)

	def test_inclusive_tax_with_not_applicable_item_tax(self):
		"""An inclusive tax row meeting an item that marks it not applicable must
		contribute no fraction, instead of raising in get_current_tax_fraction."""
		vat_19 = "_Test Account Service Tax - _TC"

		template = frappe.new_doc("Item Tax Template")
		template.title = "_Test NA Template Inclusive"
		template.company = "_Test Company"
		template.append("taxes", {"tax_type": vat_19, "tax_rate": 0, "not_applicable": 1})
		template.insert()

		so = make_sales_order(do_not_save=True)
		so.items = []
		so.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"rate": 119,
				"warehouse": "_Test Warehouse - _TC",
				"item_tax_template": template.name,
			},
		)
		so.set("taxes", [])
		so.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": vat_19,
				"description": vat_19,
				"rate": 19,
				"included_in_print_rate": 1,
				"cost_center": "_Test Cost Center - _TC",
			},
		)

		so.save()

		# the tax does not apply, so nothing is backed out of the printed rate
		self.assertEqual(so.net_total, 119.0)
		self.assertEqual(so.taxes[0].tax_amount, 0.0)
		self.assertEqual(so.taxes[0].net_amount, 0.0)
		self.assertEqual(so.grand_total, 119.0)

	def test_tax_net_amount_survives_grand_total_discount(self):
		"""A discount on Grand Total re-runs the calculation with
		discount_amount_applied set. net_amount is reset on that second pass, so
		it has to be accumulated there too instead of being left at zero."""
		so = make_sales_order(do_not_save=True)
		so.items = []
		so.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 10,
				"rate": 100,
				"warehouse": "_Test Warehouse - _TC",
			},
		)
		so.set("taxes", [])
		so.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account VAT - _TC",
				"description": "VAT",
				"rate": 19,
				"cost_center": "_Test Cost Center - _TC",
			},
		)
		so.apply_discount_on = "Grand Total"
		so.discount_amount = 100

		calculate_taxes_and_totals(so)

		self.assertEqual(so.taxes[0].net_amount, so.net_total)
		self.assertEqual(so.grand_total, 1090.0)
