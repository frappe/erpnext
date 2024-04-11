import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "material_request_item")
	frappe.reload_doc("selling", "doctype", "sales_order_item")

	for doctype in ["Sales Order", "Material Request"]:
		condition = " and child_doc.stock_qty > child_doc.produced_qty and ROUND(doc.per_delivered, 2) < 100"
		if doctype == "Material Request":
			condition = " and doc.per_ordered < 100 and doc.material_request_type = 'Manufacture'"

		frappe.db.sql(
			f""" UPDATE `tab{doctype}` as doc, `tab{doctype} Item` as child_doc, tabItem as item
			SET
				child_doc.bom_no = item.default_bom
			WHERE
				child_doc.item_code = item.name and child_doc.docstatus < 2
				and child_doc.parent = doc.name
				and item.default_bom is not null and item.default_bom != '' {condition}
		"""
		)
