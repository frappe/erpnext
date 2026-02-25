import frappe
from frappe.query_builder import Case


def execute():
	Asset = frappe.qb.DocType("Asset")

	frappe.qb.update(Asset).set(
		Asset.asset_type,
		Case()
		.when(Asset.is_existing_asset == 1, "Existing Asset")
		.when(Asset.is_composite_asset == 1, "Composite Asset")
		.when(Asset.is_composite_component == 1, "Composite Component")
		.else_(""),
	).run()
