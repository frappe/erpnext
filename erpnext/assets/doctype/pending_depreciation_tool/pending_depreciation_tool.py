# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Order
from frappe.query_builder.functions import Max, Min, Sum
from frappe.utils import getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.depreciation import (
	get_companies_with_frozen_limits,
	make_depreciation_entry,
)


class PendingDepreciationTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset_category: DF.Link | None
		company: DF.Link | None
		date: DF.Date | None
		finance_book: DF.Link | None

	# end: auto-generated types
	pass


@frappe.whitelist()
def get_pending_depreciation_assets(
	date: str,
	company: str | None = None,
	asset_category: str | None = None,
	finance_book: str | None = None,
) -> list[dict]:
	"""Return all assets that have pending depreciation entries up to ``date``."""
	a = frappe.qb.DocType("Asset")
	ads = frappe.qb.DocType("Asset Depreciation Schedule")
	ds = frappe.qb.DocType("Depreciation Schedule")

	query = (
		frappe.qb.from_(ads)
		.join(a)
		.on(ads.asset == a.name)
		.join(ds)
		.on(ads.name == ds.parent)
		.select(
			ads.name.as_("depr_schedule_name"),
			a.name.as_("asset"),
			a.asset_name,
			a.asset_category,
			ads.finance_book,
			ads.depreciation_method,
			Min(ds.schedule_date).as_("next_depreciation_date"),
			Sum(ds.depreciation_amount).as_("pending_depreciation_amount"),
			(Min(ds.idx) - 1).as_("sch_start_idx"),
			Max(ds.idx).as_("sch_end_idx"),
		)
		.where(a.calculate_depreciation == 1)
		.where(a.docstatus == 1)
		.where(ads.docstatus == 1)
		.where(a.status.isin(["Submitted", "Partially Depreciated"]))
		.where(ds.journal_entry.isnull())
		.where(ds.schedule_date <= getdate(date))
		.groupby(ads.name)
		.orderby(a.asset_name, order=Order.asc)
	)

	if company:
		query = query.where(a.company == company)

	if asset_category:
		query = query.where(a.asset_category == asset_category)

	if finance_book:
		query = query.where(ads.finance_book == finance_book)

	companies_with_frozen_limits = get_companies_with_frozen_limits()
	for comp, frozen_upto in companies_with_frozen_limits.items():
		query = query.where((a.company != comp) | (ds.schedule_date > frozen_upto))

	return query.run(as_dict=True)


@frappe.whitelist()
def create_depreciation_entries(depr_schedule_names: list | str, date: str) -> dict:
	"""Create depreciation journal entries for the given schedules."""
	import json

	if isinstance(depr_schedule_names, str):
		depr_schedule_names = json.loads(depr_schedule_names)

	if not depr_schedule_names:
		frappe.throw(_("No depreciation schedules selected."))

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	ds = frappe.qb.DocType("Depreciation Schedule")
	ads_names = list(depr_schedule_names)

	rows = (
		frappe.qb.from_(ds)
		.select(ds.parent, (Min(ds.idx) - 1).as_("start_idx"), Max(ds.idx).as_("end_idx"))
		.where(ds.parent.isin(ads_names))
		.where(ds.journal_entry.isnull())
		.where(ds.schedule_date <= getdate(date))
		.groupby(ds.parent)
	).run(as_dict=True)

	idx_map = {r.parent: (r.start_idx, r.end_idx) for r in rows}

	success, failed = [], []

	for schedule_name in depr_schedule_names:
		if schedule_name not in idx_map:
			failed.append({"name": schedule_name, "error": _("No pending entries found")})
			continue

		sch_start_idx, sch_end_idx = idx_map[schedule_name]

		try:
			make_depreciation_entry(
				schedule_name,
				date,
				sch_start_idx,
				sch_end_idx,
				accounting_dimensions,
			)
			success.append(schedule_name)
		except Exception as e:
			frappe.db.rollback()
			failed.append({"name": schedule_name, "error": str(e)})

	return {"success": success, "failed": failed}
