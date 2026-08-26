import frappe
from frappe.query_builder import Case


def execute():
<<<<<<< HEAD
	required_columns = [
		"is_existing_asset",
		"is_composite_asset",
		"is_composite_component",
	]

	# Skip patch if any required column is missing
	if not all(frappe.db.has_column("Asset", col) for col in required_columns):
		return

	Asset = frappe.qb.DocType("Asset")
=======
	# v15 sites never had is_composite_component; only migrate columns that exist.
	column_values = (
		("is_existing_asset", "Existing Asset"),
		("is_composite_asset", "Composite Asset"),
		("is_composite_component", "Composite Component"),
	)
	existing = [(col, value) for col, value in column_values if frappe.db.has_column("Asset", col)]
	if not existing:
		return
>>>>>>> 6bdc18b (fix(asset): skip missing checkbox columns in asset type patch (#58416))

	Asset = frappe.qb.DocType("Asset")
	case = Case()
	for column, value in existing:
		case = case.when(getattr(Asset, column) == 1, value)

	frappe.qb.update(Asset).set(Asset.asset_type, case.else_("")).run()
