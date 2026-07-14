# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.accounts.services.pricing.pricing_applier import should_apply
from erpnext.accounts.services.pricing.pricing_context import build_pricing_context
from erpnext.accounts.services.pricing.pricing_coupons import cancel_redemptions, record_redemption
from erpnext.accounts.services.pricing.pricing_effects import (
	FreeItemEffect,
	HeaderDiscount,
	compose_line_rate,
)
from erpnext.accounts.services.pricing.pricing_engine import PricingEngine


def record_applications(doc, method: str | None = None) -> None:
	"""hooks entry: write ledger rows at origination submit (spec section 7.4).

	Only lines the document *originated* accrue; inherited lines were
	already recorded by their upstream origination. One row per
	(scheme, line) carries the line qty and that scheme's standalone
	discount contribution in base currency.
	"""
	if not should_apply(doc):
		return
	context = build_pricing_context(doc)
	result = PricingEngine(context, doc=doc).resolve()

	rows = _build_rows(doc, context, result)
	for row in rows:
		entry = frappe.get_doc({"doctype": "Pricing Scheme Application", **row})
		entry.insert(ignore_permissions=True)
	_record_coupon_redemption(doc, context, result)


def cancel_applications(doc, method: str | None = None) -> None:
	cancel_redemptions(doc)
	frappe.db.set_value(
		"Pricing Scheme Application",
		{"voucher_type": doc.doctype, "voucher_no": doc.name},
		"is_cancelled",
		1,
	)


def _build_rows(doc, context, result) -> list[dict]:
	rows = []
	for line in context.priceable_lines():
		rows.extend(_line_rows(doc, context, result, line))
	rows.extend(_free_item_rows(doc, context, result))
	rows.extend(_header_rows(doc, result))
	return rows


def _line_rows(doc, context, result, line) -> list[dict]:
	line_effects = result.effects_for_line(line.key)
	rows = []
	for scheme in sorted({e.scheme for e in line_effects}):
		standalone = [e for e in line_effects if e.scheme == scheme]
		delta = _standalone_discount(line, standalone, result.composition, context)
		rows.append(
			_common_row(doc, scheme)
			| {
				"voucher_detail_no": line.key,
				"item_code": line.item_code,
				"qty": line.stock_qty,
				"discount_amount": flt(delta * line.qty * context.conversion_rate, 2),
			}
		)
	return rows


def _standalone_discount(line, effects, composition, context) -> float:
	"""Per-unit discount this scheme alone would produce on the manual baseline."""
	baseline = line.price_list_rate
	rate = compose_line_rate(
		baseline,
		effects,
		composition=composition,
		conversion_rate=context.conversion_rate,
		document_currency=context.currency,
	)
	return flt(baseline - rate)


def _free_item_rows(doc, context, result) -> list[dict]:
	rows = []
	for effect in result.effects:
		if not isinstance(effect, FreeItemEffect):
			continue
		source = _line_by_key(context, effect.source_line_key)
		rows.append(
			_common_row(doc, effect.scheme)
			| {
				"voucher_detail_no": effect.source_line_key,
				"item_code": effect.item_code,
				"qty": source.stock_qty if source else 0.0,
				"free_item_qty": effect.qty,
			}
		)
	return rows


def _header_rows(doc, result) -> list[dict]:
	rows = []
	for effect in result.effects:
		if isinstance(effect, HeaderDiscount):
			basis = flt(doc.get("base_net_total"))
			rows.append(
				_common_row(doc, effect.scheme)
				| {"discount_amount": flt(basis * flt(effect.percentage) / 100, 2)}
			)
	return rows


def _common_row(doc, scheme: str) -> dict:
	party_type = "Customer" if doc.get("customer") else ("Supplier" if doc.get("supplier") else None)
	return {
		"scheme": scheme,
		"company": doc.company,
		"voucher_type": doc.doctype,
		"voucher_no": doc.name,
		"party_type": party_type,
		"party": doc.get("customer") or doc.get("supplier"),
		"posting_date": doc.get("transaction_date") or doc.get("posting_date") or nowdate(),
	}


def _line_by_key(context, key: str | None):
	if not key:
		return None
	return next((line for line in context.lines if line.key == key), None)


def _record_coupon_redemption(doc, context, result) -> None:
	"""One redemption per document when any applied scheme required the coupon."""
	if not context.coupon_code:
		return
	for scheme_name in sorted({e.scheme for e in result.effects}):
		if frappe.get_cached_value("Pricing Scheme", scheme_name, "coupon_required"):
			record_redemption(doc, context.coupon_code)
			return
