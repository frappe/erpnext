import frappe


# not able to use frappe.qb because of this bug https://github.com/frappe/frappe/issues/20292
def execute():
	if frappe.db.has_column("Asset Repair", "warehouse"):
		# nosemgrep
		frappe.db.sql(
			"""UPDATE `tabAsset Repair Consumed Item` ar_item
			JOIN `tabAsset Repair` ar
			ON ar.name = ar_item.parent
			SET ar_item.warehouse = ar.warehouse
			WHERE ifnull(ar.warehouse, '') != ''"""
		)
