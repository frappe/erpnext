from collections import defaultdict

import frappe
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt


def execute():
	asset_totals = defaultdict(float)
	for adjustment in get_adjustment_totals():
		if adjustment.calculate_depreciation:
			set_finance_book_value_adjustment(adjustment)
		else:
			asset_totals[adjustment.asset] += flt(adjustment.amount)

	for asset, amount in asset_totals.items():
		frappe.db.set_value("Asset", asset, "value_adjustment_amount", amount, update_modified=False)


def get_adjustment_totals() -> list[dict]:
	AssetValueAdjustment = frappe.qb.DocType("Asset Value Adjustment")
	Asset = frappe.qb.DocType("Asset")
	finance_book = IfNull(AssetValueAdjustment.finance_book, "")

	return (
		frappe.qb.from_(AssetValueAdjustment)
		.inner_join(Asset)
		.on(Asset.name == AssetValueAdjustment.asset)
		.select(
			AssetValueAdjustment.asset,
			Asset.calculate_depreciation,
			finance_book.as_("finance_book"),
			Sum(AssetValueAdjustment.difference_amount).as_("amount"),
		)
		.where(AssetValueAdjustment.docstatus == 1)
		.groupby(AssetValueAdjustment.asset, Asset.calculate_depreciation, finance_book)
	).run(as_dict=True)


def set_finance_book_value_adjustment(adjustment: dict) -> None:
	frappe.db.set_value(
		"Asset Finance Book",
		{
			"parent": adjustment.asset,
			"parenttype": "Asset",
			"finance_book": adjustment.finance_book or ("is", "not set"),
		},
		"value_adjustment_amount",
		flt(adjustment.amount),
		update_modified=False,
	)
