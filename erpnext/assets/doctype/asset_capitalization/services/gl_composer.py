# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

import erpnext
from erpnext.assets.doctype.asset.depreciation import (
	depreciate_asset,
	get_gl_entries_on_asset_disposal,
)
from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer


class AssetCapitalizationGLComposer(BaseStockGLComposer):
	"""GL composer for Asset Capitalization.

	Builds GL entries for consumed stock items, consumed asset items (with
	depreciation side-effects), consumed service items, and the target asset debit.
	"""

	def compose(
		self,
		inventory_account_map: dict | None = None,
		default_expense_account: str | None = None,
		default_cost_center: str | None = None,
	) -> list:
		doc = self.doc
		gl_entries = []

		self.inventory_account_map = inventory_account_map or doc.get_inventory_account_map()
		self.precision = self.get_debit_field_precision()
		self.sle_map = doc.get_stock_ledger_details()

		target_account = doc.get_target_account()
		target_against: set = set()

		self._get_gl_entries_for_consumed_stock_items(gl_entries, target_account, target_against)
		self._get_gl_entries_for_consumed_asset_items(gl_entries, target_account, target_against)
		self._get_gl_entries_for_consumed_service_items(gl_entries, target_account, target_against)

		composite_component_value = doc.get_composite_component_value()
		self._get_gl_entries_for_target_item(
			gl_entries, target_account, target_against, composite_component_value
		)

		return gl_entries

	def _get_gl_entries_for_consumed_stock_items(
		self, gl_entries: list, target_account: str, target_against: set
	) -> None:
		doc = self.doc
		for item_row in doc.stock_items:
			sle_list = self.sle_map.get(item_row.name)
			if sle_list:
				_inv_dict = doc.get_inventory_account_dict(item_row, self.inventory_account_map)
				for sle in sle_list:
					stock_value_difference = flt(sle.stock_value_difference, self.precision)

					if erpnext.is_perpetual_inventory_enabled(doc.company):
						account = _inv_dict["account"]
					else:
						account = doc.get_company_default("default_expense_account")

					target_against.add(account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": account,
								"against": target_account,
								"cost_center": item_row.cost_center,
								"project": item_row.get("project") or doc.get("project"),
								"remarks": doc.get("remarks") or "Accounting Entry for Stock",
								"credit": -1 * stock_value_difference,
							},
							_inv_dict["account_currency"],
							item=item_row,
						)
					)

	def _get_gl_entries_for_consumed_asset_items(
		self, gl_entries: list, target_account: str, target_against: set
	) -> None:
		doc = self.doc
		for item in doc.asset_items:
			asset = frappe.get_doc("Asset", item.asset)

			if asset.asset_type != "Composite Component":
				if asset.calculate_depreciation:
					notes = _(
						"This schedule was created when Asset {0} was consumed through Asset Capitalization {1}."
					).format(
						frappe.utils.get_link_to_form(asset.doctype, asset.name),
						frappe.utils.get_link_to_form(doc.doctype, doc.get("name")),
					)
					depreciate_asset(asset, doc.posting_date, notes)
					asset.reload()

				fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
					asset,
					item.asset_value,
					item.get("finance_book") or doc.get("finance_book"),
					doc.get("doctype"),
					doc.get("name"),
					doc.get("posting_date"),
				)

				for gle in fixed_asset_gl_entries:
					gle["against"] = target_account
					gl_entries.append(self.get_gl_dict(gle, item=item))
					target_against.add(gle["account"])

			asset.db_set("disposal_date", doc.posting_date)
			doc.set_consumed_asset_status(asset)

	def _get_gl_entries_for_consumed_service_items(
		self, gl_entries: list, target_account: str, target_against: set
	) -> None:
		doc = self.doc
		for item_row in doc.service_items:
			expense_amount = flt(item_row.amount, self.precision)
			target_against.add(item_row.expense_account)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": item_row.expense_account,
						"against": target_account,
						"cost_center": item_row.cost_center,
						"project": item_row.get("project") or doc.get("project"),
						"remarks": doc.get("remarks") or "Accounting Entry for Stock",
						"credit": expense_amount,
					},
					item=item_row,
				)
			)

	def _get_gl_entries_for_target_item(
		self,
		gl_entries: list,
		target_account: str,
		target_against: set,
		composite_component_value: float,
	) -> None:
		doc = self.doc
		total_value = flt(doc.total_value - composite_component_value, self.precision)
		if total_value:
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": target_account,
						"against": ", ".join(target_against),
						"remarks": doc.get("remarks") or _("Accounting Entry for Asset"),
						"debit": total_value,
						"cost_center": doc.get("cost_center"),
					},
					item=doc,
				)
			)
