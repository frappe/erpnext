# Copyright (c) 2022, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if not frappe.db.table_exists("Asset"):
		return

	if not frappe.db.count("Asset"):
		return

	if frappe.db.has_column("Asset", "asset_quantity"):
		rename_field("Asset", "asset_quantity", "num_of_assets")

	if frappe.db.has_column("Item", "is_grouped_asset") and frappe.db.has_column(
		"Asset", "num_of_assets"
	):
		set_num_of_assets_for_non_grouped_assets()

	frappe.reload_doctype("Asset")
	frappe.reload_doctype("Asset Finance Book")

	if frappe.db.has_column("Asset", "is_serialized_asset"):
		make_all_assets_non_serialized()

	fix_gross_purchase_amount()

	if frappe.db.has_column("Asset", "asset_value") and frappe.db.table_exists("Asset Repair"):
		set_asset_value_for_non_depreciable_assets()

	if frappe.db.table_exists("Asset Finance Book") and frappe.db.count("Asset Finance Book"):
		if (
			frappe.db.has_column("Asset", "salvage_value")
			and frappe.db.has_column("Asset", "depeciation_posting_start_date")
			and frappe.db.has_column("Asset Finance Book", "depreciation_template")
			and frappe.db.has_column("Asset Finance Book", "asset_life_in_months")
			and frappe.db.table_exists("Depreciation Template")
			and frappe.db.has_column("Depreciation Template", "asset_life")
			and frappe.db.has_column("Depreciation Template", "asset_life_unit")
			and frappe.db.has_column("Depreciation Template", "depreciation_method")
			and frappe.db.has_column("Depreciation Template", "frequency_of_depreciation")
			and frappe.db.has_column("Depreciation Template", "rate_of_depreciation")
		):
			set_salvage_value_and_depreciation_posting_start_date()
			set_asset_life_in_months_and_asset_value()


def make_all_assets_non_serialized():
	frappe.db.sql(
		"""
		UPDATE
			`tabAsset`
		SET
			is_serialized_asset = 0
		"""
	)


def set_num_of_assets_for_non_grouped_assets():
	grouped_assets = get_grouped_assets()

	if grouped_assets:
		frappe.db.sql(
			"""
			UPDATE
				`tabAsset`
			SET
				num_of_assets = 1
			WHERE
				name not in %s
			""",
			grouped_assets,
		)


def get_grouped_assets():
	grouped_asset_items = frappe.get_all(
		"Item", filters={"is_fixed_asset": 1, "is_grouped_asset": 1}, pluck="name"
	)

	grouped_assets = frappe.get_all(
		"Asset", filters={"item_code": ["in", grouped_asset_items]}, pluck="name"
	)

	return grouped_assets


def fix_gross_purchase_amount():
	frappe.db.sql(
		"""
		UPDATE
			`tabAsset`
		SET
			gross_purchase_amount = gross_purchase_amount / num_of_assets
		WHERE
			num_of_assets > 1
		"""
	)


def set_asset_value_for_non_depreciable_assets():
	frappe.db.sql(
		"""
		UPDATE
			`tabAsset`
		SET
			asset_value = gross_purchase_amount
		WHERE
			status != "Draft"
			and calculate_depreciation = 0
		"""
	)

	if frappe.db.count("Asset Repair", {"capitalize_repair_cost": 1}):
		repair_cost_map = get_total_repair_cost_for_all_assets()
		updated_asset_values = get_updated_asset_values(repair_cost_map)

		conditions = ",".join(updated_asset_values)
		frappe.db.sql(
			"""
			INSERT INTO `tabAsset` (name, asset_value) VALUES {}
			ON DUPLICATE KEY UPDATE name = VALUES(name), asset_value = VALUES(asset_value)
		""".format(
				conditions
			)
		)


def get_total_repair_cost_for_all_assets():
	non_depreciable_assets = frappe.get_all(
		"Asset", filters={"calculate_depreciation": 0}, pluck="name"
	)

	asset_repairs = frappe.get_all(
		"Asset Repair",
		filters={
			"asset": ["in", non_depreciable_assets],
			"repair_status": "Completed",
			"capitalize_repair_cost": 1,
			"repair_cost": [">", 0],
		},
		fields=["asset", "repair_cost"],
		order_by="asset",
	)

	repair_cost_map = {}
	for repair in asset_repairs:
		if repair.asset in repair_cost_map:
			repair_cost_map[repair.asset] += repair.repair_cost
		else:
			repair_cost_map[repair.asset] = repair.repair_cost

	return repair_cost_map


def get_updated_asset_values(repair_cost_map):
	assets = list(repair_cost_map.keys())
	current_asset_values = frappe.get_all(
		"Asset", filters={"name": ["in", assets]}, fields=["name", "asset_value"]
	)

	updated_asset_values = []
	for asset in current_asset_values:
		updated_asset_values.append(
			"({0}, {1})".format(asset.name, (asset.asset_value + repair_cost_map[asset.name]))
		)

	return updated_asset_values


def set_salvage_value_and_depreciation_posting_start_date():
	frappe.db.sql(
		"""
		UPDATE
			`tabAsset` asset, `tabAsset Finance Book` fb
		SET
			asset.salvage_value = fb.expected_value_after_useful_life
			and asset.depreciation_posting_start_date = fb.depreciation_start_date
		WHERE
			asset.name = fb.parent
		"""
	)


def set_asset_life_in_months_and_asset_value():
	frappe.db.sql(
		"""
		UPDATE
			`tabAsset Finance Book`
		SET
			asset_life_in_months = total_number_of_depreciations * frequency_of_depreciation
			and asset_value = value_after_depreciation
		"""
	)
