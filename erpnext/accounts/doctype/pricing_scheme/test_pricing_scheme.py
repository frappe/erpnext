# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, flt, nowdate

from erpnext.accounts.services.pricing.pricing_context import LineContext, PricingContext
from erpnext.accounts.services.pricing.pricing_effects import (
	FreeItemEffect,
	MarginEffect,
	PercentDiscount,
	compose_line_rate,
)
from erpnext.accounts.services.pricing.pricing_engine import PricingEngine
from erpnext.tests.utils import ERPNextTestSuite

PARENT_GROUP = "_PS Parent Group"
CHILD_GROUP = "_PS Child Group"
OTHER_GROUP = "_Test Item Group"
BRAND = "_PS Brand"
ITEM_A = "_PS Item A"  # child group + brand
ITEM_B = "_PS Item B"  # child group, no brand
ITEM_C = "_PS Item C"  # other group


class TestPricingScheme(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_scope_masters()
		frappe.db.commit()  # nosemgrep — masters must survive per-test rollback

	def make_context(self, lines: list[LineContext], **overrides) -> PricingContext:
		defaults = dict(
			company="_Test Company",
			currency="INR",
			transaction_type="Selling",
			transaction_date=nowdate(),
			party_type="Customer",
			party="_Test Customer",
			customer_group="_Test Customer Group",
			lines=tuple(lines),
		)
		defaults.update(overrides)
		return PricingContext(**defaults)

	def resolve(self, context: PricingContext):
		return PricingEngine(context).resolve()

	def test_scope_include_exclude_subtree(self):
		make_scheme(
			trigger=[group_row(PARENT_GROUP), item_row(ITEM_B, exclude=1)],
			tiers=[tier(min_qty=1, value=10)],
		)
		result = self.resolve(self.make_context([line_a(), line_b(), line_c()]))

		discounted = {e.line_key for e in result.effects if isinstance(e, PercentDiscount)}
		self.assertEqual(discounted, {"A"}, "subtree include minus exclude should leave only line A")

	def test_cross_scope_type_and_semantics(self):
		make_scheme(
			trigger=[group_row(PARENT_GROUP), brand_row(BRAND)],
			tiers=[tier(min_qty=1, value=10)],
		)
		result = self.resolve(self.make_context([line_a(), line_b()]))

		discounted = {e.line_key for e in result.effects}
		self.assertEqual(discounted, {"A"}, "group AND brand must intersect, not union")

	def test_tier_selection_and_gap(self):
		make_scheme(
			trigger=[group_row(PARENT_GROUP)],
			tiers=[tier(10, 20, value=5), tier(20, 50, value=8), tier(50, 0, value=12)],
		)
		result = self.resolve(self.make_context([line_a(qty=24), line_b(qty=5)]))

		effects = {e.line_key: e.percentage for e in result.effects}
		self.assertEqual(effects, {"A": 8.0}, "qty 24 hits 20-50 tier; qty 5 sits in the gap below 10")

	def test_priority_wins_within_stacking_group(self):
		make_scheme(title="Low", trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=5)], priority=1)
		winner = make_scheme(
			title="High", trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=8)], priority=5
		)
		result = self.resolve(self.make_context([line_a()]))

		self.assertEqual([e.scheme for e in result.effects], [winner.name])
		shadowed = [t for t in result.trace.entries if t.status == "shadowed"]
		self.assertEqual(len(shadowed), 1)

	def test_composition_compound_vs_additive(self):
		effects = [
			PercentDiscount(scheme="s1", stacking_group="Default", line_key="A", percentage=10),
			PercentDiscount(scheme="s2", stacking_group="Seasonal", line_key="A", percentage=5),
		]
		self.assertAlmostEqual(compose_line_rate(100, effects, "Compound"), 85.5)
		self.assertAlmostEqual(compose_line_rate(100, effects, "Additive"), 85.0)

	def test_additive_folds_percentage_margin_on_base(self):
		# the #36789 trade-scheme case: 100 - 2% + 1% margin, both on base
		effects = [
			PercentDiscount(scheme="s1", stacking_group="Default", line_key="A", percentage=2),
			MarginEffect(
				scheme="s2", stacking_group="Seasonal", line_key="A", margin_type="Percentage", value=1
			),
		]
		self.assertAlmostEqual(compose_line_rate(100, effects, "Additive"), 99.0)
		self.assertAlmostEqual(compose_line_rate(100, effects, "Compound"), 98.98)

	def test_benefit_scope_targets_other_items(self):
		make_scheme(
			trigger=[group_row(PARENT_GROUP)],
			benefit=[item_row(ITEM_C)],
			tiers=[tier(min_qty=10, value=50)],
			aggregation="Per Document",
		)
		result = self.resolve(self.make_context([line_a(qty=12), line_c(qty=1)]))

		discounted = {e.line_key for e in result.effects}
		self.assertEqual(discounted, {"C"}, "benefit scope redirects the effect off the trigger lines")

	def test_free_item_recurrence_per_dozen(self):
		make_scheme(
			effect_type="Free Item",
			trigger=[group_row(PARENT_GROUP)],
			tiers=[tier(min_qty=12, free_qty=1, recurrence_qty=12)],
			aggregation="Per Document",
		)
		result = self.resolve(self.make_context([line_a(qty=24)]))

		free = [e for e in result.effects if isinstance(e, FreeItemEffect)]
		self.assertEqual(len(free), 1)
		self.assertEqual(free[0].item_code, ITEM_A, "blank free_item means same item")
		self.assertEqual(free[0].qty, 2.0, "24 qty at one free per dozen")

	def test_expired_scheme_never_matches(self):
		make_scheme(
			trigger=[group_row(PARENT_GROUP)],
			tiers=[tier(min_qty=1, value=10)],
			valid_upto=add_days(nowdate(), -1),
		)
		result = self.resolve(self.make_context([line_a()]))
		self.assertFalse(result.effects)

	def test_party_exclude_rejects_named_customer(self):
		make_scheme(
			trigger=[group_row(PARENT_GROUP)],
			party=[party_row("Customer", "_Test Customer", exclude=1)],
			tiers=[tier(min_qty=1, value=10)],
		)
		result = self.resolve(self.make_context([line_a()]))

		self.assertFalse(result.effects)
		reasons = [t.reason for t in result.trace.entries if t.status == "rejected"]
		self.assertIn("party not in scope", reasons)

	def test_per_period_accrues_from_ledger(self):
		scheme = make_scheme(
			trigger=[group_row(PARENT_GROUP)],
			tiers=[tier(10, 50, value=5), tier(50, 0, value=12)],
			aggregation="Per Period",
			period_window="Validity Period",
			valid_from=nowdate(),
			valid_upto=add_days(nowdate(), 30),
		)
		make_ledger_row(scheme.name, qty=30)
		result = self.resolve(self.make_context([line_a(qty=24)]))

		self.assertEqual([e.percentage for e in result.effects], [12.0], "24 now + 30 accrued crosses 50")

	def test_validation_rejects_overlapping_tiers(self):
		self.assertRaises(
			frappe.ValidationError,
			make_scheme,
			trigger=[group_row(PARENT_GROUP)],
			tiers=[tier(10, 30, value=5), tier(20, 50, value=8)],
		)

	def test_validation_requires_trigger_include_row(self):
		self.assertRaises(
			frappe.ValidationError,
			make_scheme,
			trigger=[item_row(ITEM_B, exclude=1)],
			tiers=[tier(min_qty=1, value=5)],
		)


def make_scope_masters() -> None:
	from erpnext.stock.doctype.item.test_item import make_item

	if not frappe.db.exists("Item Group", PARENT_GROUP):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": PARENT_GROUP,
				"is_group": 1,
				"parent_item_group": "All Item Groups",
			}
		).insert()
	if not frappe.db.exists("Item Group", CHILD_GROUP):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": CHILD_GROUP, "parent_item_group": PARENT_GROUP}
		).insert()
	if not frappe.db.exists("Brand", BRAND):
		frappe.get_doc({"doctype": "Brand", "brand": BRAND}).insert()

	make_item(ITEM_A, {"item_group": CHILD_GROUP, "brand": BRAND})
	make_item(ITEM_B, {"item_group": CHILD_GROUP})
	make_item(ITEM_C, {"item_group": OTHER_GROUP})


def make_scheme(**kwargs):
	doc = frappe.get_doc(
		{
			"doctype": "Pricing Scheme",
			"title": kwargs.pop("title", "Test Scheme"),
			"effect_type": kwargs.pop("effect_type", "Discount Percentage"),
			"company": kwargs.pop("company", "_Test Company"),
			"transaction_type": "Selling",
			"stacking_group": kwargs.pop("stacking_group", "Default"),
			"priority": kwargs.pop("priority", 1),
			"aggregation": kwargs.pop("aggregation", "Per Line"),
			"trigger_scope": kwargs.pop("trigger"),
			"benefit_scope": kwargs.pop("benefit", []),
			"party_scope": kwargs.pop("party", []),
			"tiers": kwargs.pop("tiers"),
			**kwargs,
		}
	)
	return doc.insert()


def make_ledger_row(scheme: str, qty: float) -> None:
	frappe.get_doc(
		{
			"doctype": "Pricing Scheme Application",
			"scheme": scheme,
			"company": "_Test Company",
			"party_type": "Customer",
			"party": "_Test Customer",
			"item_code": ITEM_A,
			"qty": qty,
			"posting_date": nowdate(),
		}
	).insert()


def group_row(value: str, exclude: int = 0) -> dict:
	return {"scope_type": "Item Group", "value": value, "exclude": exclude}


def item_row(value: str, exclude: int = 0) -> dict:
	return {"scope_type": "Item", "value": value, "exclude": exclude}


def brand_row(value: str, exclude: int = 0) -> dict:
	return {"scope_type": "Brand", "value": value, "exclude": exclude}


def party_row(party_type: str, value: str, exclude: int = 0) -> dict:
	return {"party_type": party_type, "value": value, "exclude": exclude}


def tier(min_qty: float = 0, max_qty: float = 0, **kwargs) -> dict:
	return {"min_qty": min_qty, "max_qty": max_qty, **kwargs}


def line_a(qty: float = 10) -> LineContext:
	return _line("A", ITEM_A, CHILD_GROUP, brand=BRAND, qty=qty)


def line_b(qty: float = 10) -> LineContext:
	return _line("B", ITEM_B, CHILD_GROUP, qty=qty)


def line_c(qty: float = 10) -> LineContext:
	return _line("C", ITEM_C, OTHER_GROUP, qty=qty)


def _line(
	key: str, item_code: str, item_group: str, brand: str | None = None, qty: float = 10
) -> LineContext:
	return LineContext(
		key=key,
		item_code=item_code,
		item_group=item_group,
		brand=brand,
		qty=qty,
		stock_qty=qty,
		price_list_rate=100.0,
		base_amount=qty * 100.0,
	)


class TestPricingSchemeApplier(ERPNextTestSuite):
	"""End-to-end: engine + applier on real selling documents, invariants included."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_scope_masters()
		frappe.db.commit()  # nosemgrep — masters must survive per-test rollback

	def setUp(self):
		frappe.db.set_single_value("Accounts Settings", "pricing_engine", "Pricing Scheme")
		frappe.clear_document_cache("Accounts Settings", "Accounts Settings")

	def tearDown(self):
		super().tearDown()
		frappe.clear_document_cache("Accounts Settings", "Accounts Settings")

	def make_sales_order(self, qty: float = 24, item: str = ITEM_A, do_not_submit: bool = True):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		return make_sales_order(item=item, qty=qty, price_list_rate=100, do_not_submit=do_not_submit)

	def test_discount_applied_and_idempotent(self):
		make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(20, 50, value=8)])
		so = self.make_sales_order(qty=24)

		self.assertEqual(so.items[0].rate, 92)
		self.assertEqual(so.items[0].scheme_discount_amount, 8)

		so.save()  # invariant 1: idempotency — apply twice == once
		self.assertEqual(so.items[0].rate, 92)
		self.assertEqual(so.items[0].scheme_discount_amount, 8)

	def test_reversibility_restores_baseline(self):
		scheme = make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order()
		self.assertEqual(so.items[0].rate, 90)

		scheme.disabled = 1
		scheme.save()
		so.save()  # invariant 2: reversibility — removal == baseline

		self.assertEqual(so.items[0].rate, 100)
		self.assertEqual(so.items[0].scheme_discount_amount, 0)

	def test_manual_discount_composes_and_survives(self):
		make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order(do_not_submit=True)
		so.items[0].discount_percentage = 20  # user-owned
		so.save()

		# baseline 100 -> manual 20% -> 80 -> scheme 10% -> 72
		self.assertEqual(so.items[0].rate, 72)
		self.assertEqual(so.items[0].discount_percentage, 20, "user field never touched")

	def test_untouched_lines_keep_manual_rates(self):
		make_scheme(trigger=[item_row(ITEM_A)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order(item=ITEM_C)  # out of scope
		so.items[0].rate = 77  # negotiated by hand, no price_list_rate sync
		so.items[0].price_list_rate = 0
		so.save()

		self.assertEqual(so.items[0].rate, 77, "engine must not clobber untouched lines")

	def test_free_item_row_reconciled(self):
		make_scheme(
			effect_type="Free Item",
			trigger=[group_row(PARENT_GROUP)],
			tiers=[tier(min_qty=12, free_qty=1, recurrence_qty=12)],
			aggregation="Per Document",
		)
		so = self.make_sales_order(qty=24)
		free_rows = [d for d in so.items if d.is_free_item]
		self.assertEqual([(d.item_code, d.qty, d.rate) for d in free_rows], [(ITEM_A, 2.0, 0.0)])

		so.items[0].qty = 12  # drop a dozen -> free qty must follow
		so.save()
		free_rows = [d for d in so.items if d.is_free_item]
		self.assertEqual([d.qty for d in free_rows], [1.0])

		so.items[0].qty = 5  # below tier -> free row removed
		so.save()
		self.assertFalse([d for d in so.items if d.is_free_item])

	def test_chain_stability_so_to_delivery_note(self):
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

		scheme = make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order(do_not_submit=False)
		self.assertEqual(so.items[0].rate, 90)

		# scheme changes after the order is placed
		scheme.tiers[0].value = 50
		scheme.save()

		dn = make_delivery_note(so.name)
		dn.flags.ignore_mandatory = True  # site-local custom fields are not under test
		dn.save()  # invariant 3: chain stability — DN bills what SO agreed
		self.assertEqual(dn.items[0].rate, 90)
		self.assertEqual(dn.items[0].scheme_discount_amount, 10)

	def test_line_level_ignore_flag(self):
		make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order(do_not_submit=True)
		so.items[0].ignore_pricing_scheme = 1
		so.save()

		self.assertEqual(so.items[0].rate, 100)
		self.assertEqual(so.items[0].scheme_discount_amount, 0)

	def test_ledger_written_on_submit_and_cancelled(self):
		scheme = make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order(qty=24, do_not_submit=False)

		rows = frappe.get_all(
			"Pricing Scheme Application",
			filters={"voucher_no": so.name, "is_cancelled": 0},
			fields=["scheme", "qty", "discount_amount", "party"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].scheme, scheme.name)
		self.assertEqual(rows[0].qty, 24)
		self.assertEqual(rows[0].discount_amount, 240)  # 10/unit * 24
		self.assertEqual(rows[0].party, so.customer)

		so.cancel()
		self.assertFalse(
			frappe.get_all("Pricing Scheme Application", filters={"voucher_no": so.name, "is_cancelled": 0})
		)

	def test_legacy_mode_is_fully_dormant(self):
		frappe.db.set_single_value("Accounts Settings", "pricing_engine", "Legacy")
		frappe.clear_document_cache("Accounts Settings", "Accounts Settings")
		make_scheme(trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)])
		so = self.make_sales_order()

		self.assertEqual(so.items[0].rate, 100)
		self.assertEqual(flt(so.items[0].scheme_discount_amount), 0)


class TestPricingSchemeCoupons(ERPNextTestSuite):
	"""Coupon gate, redemption ledger, chain-root uniqueness."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_scope_masters()
		frappe.db.commit()  # nosemgrep — masters must survive per-test rollback

	def setUp(self):
		frappe.db.set_single_value("Accounts Settings", "pricing_engine", "Pricing Scheme")
		frappe.clear_document_cache("Accounts Settings", "Accounts Settings")

	def tearDown(self):
		super().tearDown()
		frappe.clear_document_cache("Accounts Settings", "Accounts Settings")

	def make_coupon_setup(self, **campaign_overrides):
		scheme = make_scheme(
			trigger=[group_row(PARENT_GROUP)], tiers=[tier(1, 0, value=10)], coupon_required=1
		)
		campaign = frappe.get_doc(
			{
				"doctype": "Coupon Campaign",
				"title": "Test Campaign",
				"pricing_scheme": scheme.name,
				**campaign_overrides,
			}
		).insert()
		coupon = frappe.get_doc({"doctype": "Coupon", "code": "SAVE10", "campaign": campaign.name}).insert()
		return scheme, campaign, coupon

	def make_so(self, coupon: str | None = None, do_not_submit: bool = True):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(item=ITEM_A, qty=10, price_list_rate=100, do_not_save=True)
		so.pricing_coupon = coupon
		so.insert()
		if not do_not_submit:
			so.submit()
		return so

	def test_coupon_required_scheme_needs_valid_coupon(self):
		_, _, coupon = self.make_coupon_setup()

		without = self.make_so()
		self.assertEqual(without.items[0].rate, 100, "no coupon, no discount")

		with_coupon = self.make_so(coupon=coupon.name)
		self.assertEqual(with_coupon.items[0].rate, 90)

	def test_disabled_coupon_rejected(self):
		_, _, coupon = self.make_coupon_setup()
		coupon.status = "Disabled"
		coupon.save()

		so = self.make_so(coupon=coupon.name)
		self.assertEqual(so.items[0].rate, 100)

	def test_redemption_written_once_per_chain(self):
		_, _, coupon = self.make_coupon_setup()
		so = self.make_so(coupon=coupon.name, do_not_submit=False)

		redemption_name = f"{coupon.name}::{so.name}"
		self.assertEqual(frappe.db.get_value("Coupon Redemption", redemption_name, "status"), "Redeemed")

		# downstream SI inherits — must not redeem again
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		si = make_sales_invoice(so.name)
		si.flags.ignore_mandatory = True  # site-local custom fields are not under test
		si.pricing_coupon = coupon.name
		si.insert()
		si.submit()

		redemptions = frappe.get_all("Coupon Redemption", filters={"coupon": coupon.name})
		self.assertEqual(len(redemptions), 1, "one redemption per SO chain")

	def test_cancel_flips_redemption_status(self):
		_, _, coupon = self.make_coupon_setup()
		so = self.make_so(coupon=coupon.name, do_not_submit=False)
		so.cancel()

		self.assertEqual(
			frappe.db.get_value("Coupon Redemption", f"{coupon.name}::{so.name}", "status"),
			"Cancelled",
		)

	def test_campaign_total_limit_exhausts(self):
		_, campaign, coupon = self.make_coupon_setup(max_uses_total=1)
		self.make_so(coupon=coupon.name, do_not_submit=False)

		second = self.make_so(coupon=coupon.name)
		self.assertEqual(second.items[0].rate, 100, "limit reached, scheme must not apply")

	def test_per_customer_limit(self):
		_, campaign, coupon = self.make_coupon_setup(max_uses_per_customer=1)
		self.make_so(coupon=coupon.name, do_not_submit=False)

		second = self.make_so(coupon=coupon.name)
		self.assertEqual(second.items[0].rate, 100)

	def test_active_code_reuse_blocked_until_disabled(self):
		scheme, campaign, coupon = self.make_coupon_setup()

		clash = frappe.get_doc({"doctype": "Coupon", "code": "save10", "campaign": campaign.name})
		self.assertRaises(frappe.ValidationError, clash.insert)

		coupon.status = "Disabled"
		coupon.save()
		reissued = frappe.get_doc({"doctype": "Coupon", "code": "SAVE10", "campaign": campaign.name}).insert()
		self.assertEqual(reissued.code, "SAVE10", "code reusable once previous is disabled")
