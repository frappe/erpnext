import frappe


def execute():
	purchase_receipts = frappe.db.sql(
		"""
		SELECT
			 parent from `tabPurchase Receipt Item`
		WHERE
			material_request is not null
			AND docstatus=1
		""",
		as_dict=1,
	)

	purchase_receipts = set([d.parent for d in purchase_receipts])

	for pr in purchase_receipts:
		doc = frappe.get_doc("Purchase Receipt", pr)
		doc.status_updater = [
			{
				"source_dt": "Purchase Receipt Item",
				"target_dt": "Material Request Item",
				"join_field": "material_request_item",
				"target_field": "received_qty",
				"target_parent_dt": "Material Request",
				"target_parent_field": "per_received",
				"target_ref_field": "stock_qty",
				"source_field": "stock_qty",
				"percent_join_field": "material_request",
			}
		]
		doc.update_qty()
