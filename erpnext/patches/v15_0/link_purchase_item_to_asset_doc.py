import frappe


def execute():
	if frappe.db.has_column("Asset", "purchase_invoice_item") and frappe.db.has_column(
		"Asset", "purchase_receipt_item"
	):
		# Get all assets with their related Purchase Invoice and Purchase Receipt
		assets = frappe.get_all(
			"Asset",
			filters={"docstatus": 0},
			fields=[
				"name",
				"item_code",
				"purchase_invoice",
				"purchase_receipt",
				"gross_purchase_amount",
				"asset_quantity",
				"purchase_invoice_item",
				"purchase_receipt_item",
			],
		)

		for asset in assets:
			# Get Purchase Invoice Items
			if asset.purchase_invoice and not asset.purchase_invoice_item:
				purchase_invoice_item = get_linked_item(
					"Purchase Invoice Item",
					asset.purchase_invoice,
					asset.item_code,
					asset.gross_purchase_amount,
					asset.asset_quantity,
				)
				frappe.db.set_value("Asset", asset.name, "purchase_invoice_item", purchase_invoice_item)

			# Get Purchase Receipt Items
			if asset.purchase_receipt and not asset.purchase_receipt_item:
				purchase_receipt_item = get_linked_item(
					"Purchase Receipt Item",
					asset.purchase_receipt,
					asset.item_code,
					asset.gross_purchase_amount,
					asset.asset_quantity,
				)
				frappe.db.set_value("Asset", asset.name, "purchase_receipt_item", purchase_receipt_item)


def get_linked_item(doctype, parent, item_code, amount, quantity):
	items = frappe.get_all(
		doctype,
		filters={
			"parenttype": doctype.replace(" Item", ""),
			"parent": parent,
			"item_code": item_code,
		},
		fields=["name", "rate", "amount", "qty", "landed_cost_voucher_amount"],
	)
	if len(items) == 1:
		# If only one item exists, return it directly
		return items[0].name

	for item in items:
		landed_cost = item.get("landed_cost_voucher_amount", 0)
		# Check if the asset is grouped
		if quantity > 1:
			if item.amount + landed_cost == amount and item.qty == quantity:
				return item.name
			elif item.qty == quantity:
				return item.name
		else:
			if item.rate + (landed_cost / item.qty) == amount:
				return item.name

	return items[0].name if items else None
