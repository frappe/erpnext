# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt
from pypika import Order


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
	if hasattr(context.doc, "set_indicator"):
		context.doc.set_indicator()

	context.parents = frappe.form_dict.parents
	context.title = frappe.form_dict.name

	if not frappe.has_website_permission(context.doc):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	default_print_format = frappe.db.get_value(
		"Property Setter",
		dict(property="default_print_format", doc_type=frappe.form_dict.doctype),
		"value",
	)
	if default_print_format:
		context.print_format = default_print_format
	else:
		context.print_format = "Standard"
	context.doc.items = get_more_items_info(context.doc.items, context.doc.name)


def get_more_items_info(items, material_request):
	work_order = frappe.qb.DocType("Work Order")
	work_order_item = frappe.qb.DocType("Work Order Item")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")

	for item in items:
		item.customer_provided = frappe.get_value("Item", item.item_code, "is_customer_provided_item")
		item.work_orders = (
			frappe.qb.from_(work_order_item)
			.join(work_order)
			.on(work_order_item.parent == work_order.name)
			.select(work_order.name, work_order.status, work_order_item.consumed_qty)
			.where(
				(work_order_item.item_code == item.item_code)
				& (work_order_item.consumed_qty == 0)
				& (work_order.status.notin(["Completed", "Cancelled", "Stopped"]))
			)
			.orderby(work_order.name, order=Order.asc)
		).run(as_dict=True)
		item.delivered_qty = flt(
			frappe.qb.from_(stock_entry_detail)
			.select(Sum(stock_entry_detail.transfer_qty))
			.where(
				(stock_entry_detail.material_request == material_request)
				& (stock_entry_detail.item_code == item.item_code)
				& (stock_entry_detail.docstatus == 1)
			)
			.run()[0][0]
		)
	return items
