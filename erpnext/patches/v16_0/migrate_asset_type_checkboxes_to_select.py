import frappe
from frappe.query_builder import Case


def execute():
	required_columns = [
		"is_existing_asset",
		"is_composite_asset",
		"is_composite_component",
	]

	# Skip patch if any required column is missing
	if not all(frappe.db.has_column("Asset", col) for col in required_columns):
		return

	Asset = frappe.qb.DocType("Asset")

	frappe.qb.update(Asset).set(
		Asset.asset_type,
		Case()
		.when(Asset.is_existing_asset == 1, "Existing Asset")
		.when(Asset.is_composite_asset == 1, "Composite Asset")
		.when(Asset.is_composite_component == 1, "Composite Component")
		.else_(""),
	).run()
