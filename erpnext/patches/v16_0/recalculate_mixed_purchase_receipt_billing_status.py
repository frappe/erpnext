import frappe

from erpnext.patches.v16_0.recalculate_purchase_receipt_billing_status import (
	exclude_purchase_order_items_with_invoice_created_receipts,
	get_candidate_purchase_order_items,
)
from erpnext.stock.doctype.purchase_receipt.services.billing_status import (
	update_billed_amount_based_on_po,
	update_billing_percentage,
)


def execute():
	purchase_order_items = get_candidate_purchase_order_items()
	if purchase_order_items:
		purchase_order_items = exclude_purchase_order_items_with_invoice_created_receipts(
			purchase_order_items
		)

	if not purchase_order_items:
		return

	updated_purchase_receipts = update_billed_amount_based_on_po(purchase_order_items)
	for purchase_receipt in set(updated_purchase_receipts):
		update_billing_percentage(frappe.get_doc("Purchase Receipt", purchase_receipt))
