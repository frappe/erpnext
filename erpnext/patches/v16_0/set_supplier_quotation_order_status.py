import frappe
from frappe.query_builder.functions import Sum


def execute():
	supplier_quotation_item = frappe.qb.DocType("Supplier Quotation Item")
	purchase_order_item = frappe.qb.DocType("Purchase Order Item")

	frappe.qb.update(supplier_quotation_item).set(supplier_quotation_item.ordered_qty, 0).run()

	ordered_items = (
		frappe.qb.from_(purchase_order_item)
		.select(
			purchase_order_item.supplier_quotation_item,
			purchase_order_item.supplier_quotation,
			Sum(purchase_order_item.stock_qty).as_("ordered_qty"),
		)
		.where(
			(purchase_order_item.docstatus == 1)
			& purchase_order_item.supplier_quotation_item.isnotnull()
			& (purchase_order_item.supplier_quotation_item != "")
			& purchase_order_item.supplier_quotation.isnotnull()
			& (purchase_order_item.supplier_quotation != "")
		)
		.groupby(
			purchase_order_item.supplier_quotation_item,
			purchase_order_item.supplier_quotation,
		)
	).run(as_dict=True)

	frappe.db.bulk_update(
		"Supplier Quotation Item",
		{item.supplier_quotation_item: {"ordered_qty": item.ordered_qty} for item in ordered_items},
		update_modified=False,
	)

	for supplier_quotation in {item.supplier_quotation for item in ordered_items}:
		frappe.get_doc("Supplier Quotation", supplier_quotation).set_status(
			update=True, update_modified=False
		)
