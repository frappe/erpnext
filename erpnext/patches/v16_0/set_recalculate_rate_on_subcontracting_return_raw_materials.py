import frappe


def execute():
	"""Let reposts revalue the raw materials that existing Subcontracting Receipt returns bring back."""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	supplied_item = frappe.qb.DocType("Subcontracting Receipt Supplied Item")
	receipt = frappe.qb.DocType("Subcontracting Receipt")

	returned_rows = (
		frappe.qb.from_(supplied_item)
		.join(receipt)
		.on(receipt.name == supplied_item.parent)
		.select(supplied_item.name)
		.where(receipt.is_return == 1)
	)

	(
		frappe.qb.update(sle)
		.set(sle.recalculate_rate, 1)
		.where(
			(sle.voucher_type == "Subcontracting Receipt")
			& (sle.recalculate_rate == 0)
			& sle.voucher_detail_no.isin(returned_rows)
		)
	).run()
