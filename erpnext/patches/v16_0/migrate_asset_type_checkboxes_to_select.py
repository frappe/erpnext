import frappe
from frappe.query_builder import Case


def execute():
	# v15 sites never had is_composite_component; only migrate columns that exist.
	column_values = (
		("is_existing_asset", "Existing Asset"),
		("is_composite_asset", "Composite Asset"),
		("is_composite_component", "Composite Component"),
	)
	existing = [(col, value) for col, value in column_values if frappe.db.has_column("Asset", col)]
	if not existing:
		return

	Asset = frappe.qb.DocType("Asset")
	case = Case()
	for column, value in existing:
		case = case.when(getattr(Asset, column) == 1, value)

	frappe.qb.update(Asset).set(Asset.asset_type, case.else_("")).run()
