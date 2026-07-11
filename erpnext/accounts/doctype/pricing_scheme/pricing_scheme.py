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
		self.validate_dates()
		self.validate_scope_rows()
		self.validate_tiers()
		self.validate_period()
		self.validate_condition()

	def validate_dates(self) -> None:
		self.validate_from_to_dates("valid_from", "valid_upto")

	def validate_scope_rows(self) -> None:
		if not any(not row.exclude for row in self.trigger_scope):
			frappe.throw(_("Trigger Scope needs at least one include row."))

		for table in ("trigger_scope", "benefit_scope"):
			for row in self.get(table):
				if row.scope_type != "All Items" and not row.value:
					frappe.throw(
						_("Row {0} in {1}: Value is required for scope type {2}.").format(
							row.idx, _(self.meta.get_label(table)), _(row.scope_type)
						)
					)

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

	def validate_condition(self) -> None:
		if not self.condition:
			return
		try:
			frappe.safe_eval(self.condition, eval_locals=_sample_condition_context())
		except Exception as exc:
			frappe.throw(_("Condition is invalid: {0}").format(exc))


def _sample_condition_context() -> dict:
	"""Synthetic document context used to dry-run conditions at save time."""
	return frappe._dict(
		doctype="Sales Order",
		company="",
		customer="",
		grand_total=0.0,
		total_qty=0.0,
		items=[],
	)
