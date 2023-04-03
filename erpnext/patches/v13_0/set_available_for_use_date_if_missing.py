import frappe


def execute():
	"""
	Sets available-for-use date for Assets created in older versions of ERPNext,
	before the field was introduced.
	"""

	assets = get_assets_without_available_for_use_date()

	for asset in assets:
		frappe.db.set_value("Asset", asset.name, "available_for_use_date", asset.purchase_date)


def get_assets_without_available_for_use_date():
	return frappe.get_all(
		"Asset", filters={"available_for_use_date": ["in", ["", None]]}, fields=["name", "purchase_date"]
	)
