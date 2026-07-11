# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.accounts.services.pricing.pricing_context import (
	LineContext,
	PricingContext,
	get_discount_composition,
)
from erpnext.accounts.services.pricing.pricing_effects import compose_line_rate
from erpnext.accounts.services.pricing.pricing_engine import PricingEngine


@frappe.whitelist()
def preview_pricing(
	company: str,
	customer: str | None = None,
	transaction_date: str | None = None,
	items: str | list | None = None,
	price_list: str | None = None,
	coupon: str | None = None,
) -> dict:
	"""Price a synthetic cart and return composed rates plus the full trace.

	Backs the Test Pricing dialog on the scheme form; the same call serves
	transaction-side "why didn't scheme X apply" debugging.
	"""
	rows = frappe.parse_json(items) if isinstance(items, str) else (items or [])
	context = _build_context(company, customer, transaction_date, rows, price_list, coupon)
	result = PricingEngine(context).resolve()

	lines = []
	for line in context.lines:
		final_rate = compose_line_rate(
			line.price_list_rate,
			result.effects_for_line(line.key),
			composition=result.composition,
			conversion_rate=context.conversion_rate,
			document_currency=context.currency,
		)
		lines.append(
			{
				"item_code": line.item_code,
				"qty": line.qty,
				"base_rate": line.price_list_rate,
				"final_rate": flt(final_rate, 2),
				"schemes": sorted({e.scheme for e in result.effects_for_line(line.key)}),
			}
		)
	free_items = [
		{"item_code": e.item_code, "qty": e.qty, "rate": e.rate, "scheme": e.scheme}
		for e in result.effects
		if type(e).__name__ == "FreeItemEffect"
	]
	return {"lines": lines, "free_items": free_items, "trace": result.trace.as_list()}


def _build_context(company, customer, transaction_date, rows, price_list, coupon) -> PricingContext:
	party = (
		frappe.get_cached_value("Customer", customer, ("customer_group", "territory"), as_dict=True)
		if customer
		else frappe._dict()
	)
	return PricingContext(
		company=company,
		currency=frappe.get_cached_value("Company", company, "default_currency"),
		transaction_type="Selling",
		transaction_date=transaction_date or nowdate(),
		party_type="Customer" if customer else None,
		party=customer,
		customer_group=party.get("customer_group"),
		territory=party.get("territory"),
		price_list=price_list,
		coupon_code=coupon,
		composition=get_discount_composition(),
		lines=tuple(
			_build_line(row, idx, price_list) for idx, row in enumerate(rows) if row.get("item_code")
		),
	)


def _build_line(row: dict, idx: int, price_list: str | None) -> LineContext:
	item = frappe.get_cached_value(
		"Item", row["item_code"], ("item_group", "brand", "variant_of", "stock_uom"), as_dict=True
	)
	qty = flt(row.get("qty")) or 1.0
	rate = flt(row.get("rate")) or _price_list_rate(row["item_code"], price_list)
	return LineContext(
		key=f"preview-{idx}",
		item_code=row["item_code"],
		item_group=item.item_group,
		brand=item.brand,
		variant_of=item.variant_of,
		qty=qty,
		stock_qty=qty,
		uom=item.stock_uom,
		price_list_rate=rate,
		base_amount=qty * rate,
	)


def _price_list_rate(item_code: str, price_list: str | None) -> float:
	filters = {"item_code": item_code, "selling": 1}
	if price_list:
		filters["price_list"] = price_list
	rate = frappe.get_all(
		"Item Price", filters=filters, fields=["price_list_rate"], order_by="valid_from desc", limit=1
	)
	return flt(rate[0].price_list_rate) if rate else 0.0
