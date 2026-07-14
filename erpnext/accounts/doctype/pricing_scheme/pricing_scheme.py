# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PricingScheme(Document):
	"""A promotion: trigger scope x benefit scope x party scope x tiers.

	Resolution semantics live in erpnext.accounts.services.pricing; this
	controller owns authoring-time validation only.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pricing_scheme_item_scope.pricing_scheme_item_scope import (
			PricingSchemeItemScope,
		)
		from erpnext.accounts.doctype.pricing_scheme_party_scope.pricing_scheme_party_scope import (
			PricingSchemePartyScope,
		)
		from erpnext.accounts.doctype.pricing_scheme_tier.pricing_scheme_tier import PricingSchemeTier

		aggregation: DF.Literal["Per Line", "Per Document", "Per Period"]
		applies_to: DF.Literal["All Items", "Specific Items"]
		apply_discount_on: DF.Literal["Grand Total", "Net Total"]
		benefit_scope: DF.Table[PricingSchemeItemScope]
		cap_total_applications: DF.Int
		cap_total_discount_amount: DF.Currency
		company: DF.Link | None
		condition: DF.Code | None
		coupon_required: DF.Check
		currency: DF.Link | None
		disabled: DF.Check
		effect_type: DF.Literal[
			"Rate", "Discount Percentage", "Discount Amount", "Margin", "Free Item", "Header Discount"
		]
		legacy_pricing_rule: DF.Data | None
		party_scope: DF.Table[PricingSchemePartyScope]
		period_days: DF.Int
		period_window: DF.Literal["Validity Period", "Rolling N Days"]
		price_list: DF.Link | None
		priority: DF.Int
		stacking_group: DF.Literal["Default", "Seasonal", "Loyalty"]
		tiers: DF.Table[PricingSchemeTier]
		title: DF.Data
		transaction_type: DF.Literal["Selling", "Buying"]
		trigger_scope: DF.Table[PricingSchemeItemScope]
		valid_from: DF.Datetime | None
		valid_upto: DF.Datetime | None
		warehouse: DF.Link | None
	# end: auto-generated types

	def validate(self) -> None:
		self.normalize_scope()
		self.validate_dates()
		self.validate_scope_rows()
		self.validate_tiers()
		self.validate_period()
		self.validate_condition()
		self.validate_no_conflicting_schemes()

	def validate_dates(self) -> None:
		self.validate_from_to_dates("valid_from", "valid_upto")

	def normalize_scope(self) -> None:
		"""Applies To is authoritative. Documents predating the field infer it
		from their rows; explicit All Items rows are the legacy representation
		and are dropped in favor of the flag."""
		legacy_rows = [row for row in self.trigger_scope if row.scope_type == "All Items"]
		if not self.applies_to:
			self.applies_to = "All Items" if legacy_rows else "Specific Items"
		if self.applies_to == "All Items" and legacy_rows:
			self.set("trigger_scope", [r for r in self.trigger_scope if r.scope_type != "All Items"])
			for idx, row in enumerate(self.trigger_scope, start=1):
				row.idx = idx

	def validate_scope_rows(self) -> None:
		if self.applies_to == "All Items":
			self.validate_exclusion_only_scope()
		else:
			self.validate_specific_scope()

		for table in ("trigger_scope", "benefit_scope"):
			for row in self.get(table):
				if row.scope_type != "All Items" and not row.value:
					frappe.throw(
						_("Row {0} in {1}: Value is required for scope type {2}.").format(
							row.idx, _(self.meta.get_label(table)), _(row.scope_type)
						)
					)

	def validate_exclusion_only_scope(self) -> None:
		for row in self.trigger_scope:
			if not row.exclude:
				frappe.throw(
					_(
						"Row {0} in Trigger Scope: the scheme already applies to all items, so scope rows must be exclusions. Check Exclude or set Applies To to Specific Items."
					).format(row.idx)
				)

	def validate_specific_scope(self) -> None:
		if any(row.scope_type == "All Items" for row in self.trigger_scope):
			frappe.throw(
				_("All Items rows are not allowed in Trigger Scope. Set Applies To to All Items instead.")
			)
		if not any(not row.exclude for row in self.trigger_scope):
			frappe.throw(_("Trigger Scope needs at least one include row."))

	def validate_tiers(self) -> None:
		for tier in self.tiers:
			self.validate_tier_bounds(tier)
			self.validate_tier_value(tier)
		self.validate_tier_overlap()

	def validate_tier_bounds(self, tier) -> None:
		if tier.max_qty and flt(tier.min_qty) >= flt(tier.max_qty):
			frappe.throw(_("Tier row {0}: Min Qty must be less than Max Qty.").format(tier.idx))
		if tier.max_amount and flt(tier.min_amount) >= flt(tier.max_amount):
			frappe.throw(_("Tier row {0}: Min Amount must be less than Max Amount.").format(tier.idx))

	def validate_tier_value(self, tier) -> None:
		if self.effect_type == "Discount Percentage" and flt(tier.value) > 100:
			frappe.throw(_("Tier row {0}: Discount Percentage cannot exceed 100.").format(tier.idx))
		if self.effect_type == "Margin" and not tier.margin_type:
			frappe.throw(_("Tier row {0}: Margin Type is required for Margin schemes.").format(tier.idx))
		if self.effect_type == "Free Item" and not flt(tier.free_qty):
			frappe.throw(_("Tier row {0}: Free Qty is required for Free Item schemes.").format(tier.idx))

	def validate_tier_overlap(self) -> None:
		from itertools import pairwise

		bands = sorted((flt(t.min_qty), flt(t.max_qty) or float("inf"), t.idx) for t in self.tiers)
		for (_min1, max1, idx1), (min2, _max2, idx2) in pairwise(bands):
			if min2 < max1:
				frappe.throw(_("Tier rows {0} and {1} have overlapping quantity bands.").format(idx1, idx2))

	def validate_period(self) -> None:
		if self.aggregation != "Per Period":
			return
		if self.period_window == "Validity Period" and not (self.valid_from and self.valid_upto):
			frappe.throw(
				_("Per Period schemes with a Validity Period window need Valid From and Valid Upto.")
			)
		if self.period_window == "Rolling N Days" and not self.period_days:
			frappe.throw(_("Per Period schemes with a rolling window need Period Days."))

	def validate_no_conflicting_schemes(self) -> None:
		"""Spec section 7.3: same stacking group + same priority + intersecting
		scope and validity must be resolved at authoring, never at data entry."""
		if self.disabled:
			return
		from erpnext.accounts.services.pricing.pricing_overlaps import detect_overlaps

		conflicts = [o for o in detect_overlaps(self) if o["severity"] == "conflict"]
		if conflicts:
			names = ", ".join(f"{o['scheme']} ({o['title']})" for o in conflicts)
			frappe.throw(
				_(
					"This scheme conflicts with {0}: same stacking group and priority over an intersecting scope. Set a different Priority or Stacking Group."
				).format(names),
				title=_("Conflicting Pricing Scheme"),
			)

	def validate_condition(self) -> None:
		if not self.condition:
			return
		try:
			frappe.safe_eval(self.condition, eval_locals=_sample_condition_context())
		except SyntaxError as exc:
			frappe.throw(_("Condition has a syntax error: {0}").format(exc))
		except Exception as exc:
			frappe.msgprint(
				_(
					"Condition could not be dry-run against a sample document: {0}. It will be evaluated live; if it fails there, the scheme will not apply."
				).format(exc),
				indicator="orange",
			)


class _SampleConditionContext(dict):
	"""Unknown field names resolve to None, so dry-running a condition never
	raises NameError for fields the sample document does not carry."""

	def __missing__(self, key: str) -> None:
		return None


def _sample_condition_context() -> dict:
	"""Synthetic document context used to dry-run conditions at save time."""
	return _SampleConditionContext(
		doctype="Sales Order",
		company="",
		customer="",
		grand_total=0.0,
		total_qty=0.0,
		items=[],
	)
