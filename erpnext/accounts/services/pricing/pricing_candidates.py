# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull

from erpnext.accounts.services.pricing.pricing_context import PricingContext


class CandidateRepository:
	"""One coarse query per document; precise matching happens in Python.

	Deliberately over-fetches: header gates only (enabled, direction,
	company, price list, validity window). Scope, party, tiers, caps,
	and conditions are evaluated by the Matcher stages.
	"""

	def fetch(self, context: PricingContext) -> list:
		return [frappe.get_cached_doc("Pricing Scheme", name) for name in self._fetch_names(context)]

	def _fetch_names(self, context: PricingContext) -> list[str]:
		from frappe.utils import getdate

		# IFNULL(datetime, varchar) compares as string — bounds must be full datetimes
		date = getdate(context.transaction_date)
		day_start, day_end = f"{date} 00:00:00", f"{date} 23:59:59"

		scheme = frappe.qb.DocType("Pricing Scheme")
		query = (
			frappe.qb.from_(scheme)
			.select(scheme.name)
			.where(scheme.disabled == 0)
			.where(scheme.transaction_type == context.transaction_type)
			.where(Criterion.any([scheme.company == context.company, IfNull(scheme.company, "") == ""]))
			.where(IfNull(scheme.valid_from, "2000-01-01 00:00:00") <= day_end)
			.where(IfNull(scheme.valid_upto, "2500-12-31 23:59:59") >= day_start)
			.orderby(scheme.name)
		)
		query = self._add_price_list_gate(query, scheme, context)
		return [row[0] for row in query.run()]

	def _add_price_list_gate(self, query, scheme, context: PricingContext):
		conditions = [IfNull(scheme.price_list, "") == ""]
		if context.price_list:
			conditions.append(scheme.price_list == context.price_list)
		return query.where(Criterion.any(conditions))


def get_accrued_basis(scheme, context: PricingContext) -> tuple[float, float]:
	"""Sum qty and discount already applied for a Per Period scheme from the ledger."""
	filters = {"scheme": scheme.name, "is_cancelled": 0, "company": context.company}
	if scheme.party_scope and context.party:
		filters["party"] = context.party
	if window := _accrual_window(scheme, context):
		filters["posting_date"] = ("between", window)

	rows = frappe.get_all("Pricing Scheme Application", filters=filters, fields=["qty", "discount_amount"])
	return (
		sum(row.qty or 0.0 for row in rows),
		sum(row.discount_amount or 0.0 for row in rows),
	)


def get_cap_usage(scheme) -> tuple[int, float]:
	"""Applications count and discount spend, for cap checks."""
	from frappe.query_builder.functions import Count, Sum

	app = frappe.qb.DocType("Pricing Scheme Application")
	rows = (
		frappe.qb.from_(app)
		.select(Count(app.name).as_("applications"), Sum(app.discount_amount).as_("spend"))
		.where((app.scheme == scheme.name) & (app.is_cancelled == 0))
		.run(as_dict=True)
	)
	row = rows[0] if rows else frappe._dict()
	return int(row.get("applications") or 0), float(row.get("spend") or 0.0)


def _accrual_window(scheme, context: PricingContext) -> tuple[str, str] | None:
	from frappe.utils import add_days, getdate

	if scheme.period_window == "Rolling N Days" and scheme.period_days:
		end = getdate(context.transaction_date)
		return (str(add_days(end, -scheme.period_days)), str(end))
	if scheme.valid_from and scheme.valid_upto:
		return (str(getdate(scheme.valid_from)), str(getdate(scheme.valid_upto)))
	return None
