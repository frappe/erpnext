import frappe
from frappe.query_builder import Case

CHECKBOX_TO_ASSET_TYPE = {
	"is_existing_asset": "Existing Asset",
	"is_composite_asset": "Composite Asset",
	"is_composite_component": "Composite Component",
}


def execute():
	columns = [f for f in CHECKBOX_TO_ASSET_TYPE if frappe.db.has_column("Asset", f)]
	if not columns:
		return

	Asset = frappe.qb.DocType("Asset")

	case = Case()
	for fieldname in columns:
		case = case.when(Asset[fieldname] == 1, CHECKBOX_TO_ASSET_TYPE[fieldname])

	# only fill in unset rows, so re-running cannot overwrite a type set from the new field
	(
		frappe.qb.update(Asset)
		.set(Asset.asset_type, case.else_(""))
		.where(Asset.asset_type.isnull() | (Asset.asset_type == ""))
		.run()
	)
