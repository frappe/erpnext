# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Fixed asset lifecycle helpers for Sales Invoice."""

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form

from erpnext.assets.doctype.asset.depreciation import (
	depreciate_asset,
	reset_depreciation_schedule,
	reverse_depreciation_entry_made_on_disposal,
)
from erpnext.assets.doctype.asset.mapper import split_asset
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity


class FixedAssetService:
	def __init__(self, doc):
		self.doc = doc

	def validate_fixed_asset(self) -> None:
		doc = self.doc
		if doc.doctype != "Sales Invoice":
			return

		for d in doc.get("items"):
			if not d.is_fixed_asset:
				continue

			if d.asset:
				if not doc.is_return:
					asset_status = frappe.db.get_value("Asset", d.asset, "status")
					if doc.update_stock:
						frappe.throw(_("'Update Stock' cannot be checked for fixed asset sale"))
					elif asset_status in ("Scrapped", "Cancelled", "Capitalized"):
						frappe.throw(
							_("Row #{0}: Asset {1} cannot be sold, it is already {2}").format(
								d.idx, d.asset, asset_status
							)
						)
					elif asset_status == "Sold" and not doc.is_return:
						frappe.throw(_("Row #{0}: Asset {1} is already sold").format(d.idx, d.asset))
				elif not doc.return_against:
					frappe.throw(_("Row #{0}: Return Against is required for returning asset").format(d.idx))
			else:
				frappe.throw(
					_("Row #{0}: You must select an Asset for Item {1}.").format(d.idx, d.item_code),
					title=_("Missing Asset"),
				)

	def set_income_account_for_fixed_assets(self) -> None:
		for item in self.doc.items:
			item.set_income_account_for_fixed_asset(self.doc.company)

	def process_asset_depreciation(self) -> None:
		doc = self.doc
		if doc.is_internal_transfer():
			return

		if (doc.is_return and doc.docstatus == 2) or (not doc.is_return and doc.docstatus == 1):
			self._depreciate_asset_on_sale()
		else:
			self._restore_asset()

		self._update_asset()

	def split_asset_based_on_sale_qty(self) -> None:
		asset_qty_map = self._get_asset_qty()
		for asset, qty in asset_qty_map.items():
			if qty["actual_qty"] < qty["sale_qty"]:
				frappe.throw(
					_(
						"Sell quantity cannot exceed the asset quantity. Asset {0} has only {1} item(s)."
					).format(asset, qty["actual_qty"])
				)

			remaining_qty = qty["actual_qty"] - qty["sale_qty"]
			if remaining_qty > 0:
				split_asset(asset, remaining_qty)

	def get_disposal_date(self) -> str:
		doc = self.doc
		if doc.is_return:
			return frappe.db.get_value("Sales Invoice", doc.return_against, "posting_date")
		return doc.posting_date

	def _depreciate_asset_on_sale(self) -> None:
		disposal_date = self.get_disposal_date()
		for d in self.doc.get("items"):
			if d.asset:
				asset = frappe.get_doc("Asset", d.asset)
				if asset.calculate_depreciation and asset.status != "Fully Depreciated":
					depreciate_asset(asset, disposal_date, self._get_note_for_asset_sale(asset))

	def _restore_asset(self) -> None:
		for d in self.doc.get("items"):
			if d.asset:
				asset = frappe.get_cached_doc("Asset", d.asset)
				if asset.calculate_depreciation:
					reverse_depreciation_entry_made_on_disposal(asset)
					reset_depreciation_schedule(asset, self._get_note_for_asset_return(asset))

	def _update_asset(self) -> None:
		doc = self.doc
		disposal_date = self.get_disposal_date()

		for d in doc.get("items"):
			if not d.asset:
				continue

			asset = frappe.get_cached_doc("Asset", d.asset)

			if (doc.is_return and doc.docstatus == 1) or (not doc.is_return and doc.docstatus == 2):
				note = _("Asset returned") if doc.is_return else _("Asset sold")
				asset_status, disposal_date = None, None
			else:
				note = _("Asset sold") if not doc.is_return else _("Return invoice of asset cancelled")
				asset_status = "Sold"

			frappe.db.set_value("Asset", d.asset, "disposal_date", disposal_date)
			add_asset_activity(asset.name, note)
			asset.set_status(asset_status)

	def _get_asset_qty(self) -> dict:
		doc = self.doc
		asset_qty_map = {}

		assets = {row.asset for row in doc.items if row.is_fixed_asset and row.asset}
		if not assets or doc.is_return:
			return asset_qty_map

		asset_actual_qty = dict(
			frappe.db.get_all(
				"Asset",
				{"name": ["in", list(assets)]},
				["name", "asset_quantity"],
				as_list=True,
			)
		)
		for row in doc.items:
			if row.is_fixed_asset and row.asset:
				actual_qty = asset_actual_qty.get(row.asset)
				if row.asset in asset_qty_map:
					asset_qty_map[row.asset]["sale_qty"] += flt(row.qty)
				else:
					asset_qty_map[row.asset] = {
						"sale_qty": flt(row.qty),
						"actual_qty": flt(actual_qty),
					}

		return asset_qty_map

	def _get_note_for_asset_sale(self, asset) -> str:
		doc = self.doc
		return _("This schedule was created when Asset {0} was {1} through Sales Invoice {2}.").format(
			get_link_to_form(asset.doctype, asset.name),
			_("returned") if doc.is_return else _("sold"),
			get_link_to_form(doc.doctype, doc.get("name")),
		)

	def _get_note_for_asset_return(self, asset) -> str:
		doc = self.doc
		asset_link = get_link_to_form(asset.doctype, asset.name)
		invoice_link = get_link_to_form(doc.doctype, doc.get("name"))
		if doc.is_return:
			return _(
				"This schedule was created when Asset {0} was returned through Sales Invoice {1}."
			).format(asset_link, invoice_link)
		return _(
			"This schedule was created when Asset {0} was restored due to Sales Invoice {1} cancellation."
		).format(asset_link, invoice_link)
