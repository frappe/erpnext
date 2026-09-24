import frappe


def execute():
	set_conversion_rates()
	set_company_currency_service_amounts()

	for name in frappe.get_all(
		"Subcontracting Order",
		filters={"docstatus": ["<", 2], "conversion_rate": ["!=", 1]},
		pluck="name",
	):
		recost_order(frappe.get_doc("Subcontracting Order", name))

	update_draft_receipts()


def set_conversion_rates():
	order = frappe.qb.DocType("Subcontracting Order")
	purchase_order = frappe.qb.DocType("Purchase Order")
	rates = (
		frappe.qb.from_(order)
		.join(purchase_order)
		.on(purchase_order.name == order.purchase_order)
		.select(order.name, purchase_order.conversion_rate)
		.where((order.docstatus < 2) & (purchase_order.conversion_rate != 1))
		.run()
	)
	frappe.db.bulk_update(
		"Subcontracting Order",
		{name: {"conversion_rate": rate} for name, rate in rates},
		update_modified=False,
	)


def set_company_currency_service_amounts():
	order = frappe.qb.DocType("Subcontracting Order")
	service_item = frappe.qb.DocType("Subcontracting Order Service Item")
	company_currency_orders = (
		frappe.qb.from_(order).select(order.name).where((order.docstatus < 2) & (order.conversion_rate == 1))
	)
	(
		frappe.qb.update(service_item)
		.set(service_item.base_rate, service_item.rate)
		.set(service_item.base_amount, service_item.amount)
		.where(service_item.parent.isin(company_currency_orders))
		.run()
	)


def recost_order(order):
	rows = order.items + order.service_items
	if all(row.purchase_order_item for row in rows):
		order.calculate_service_costs()
	else:
		set_service_costs_by_position(order)

	order.calculate_items_qty_and_amount()
	order.db_update()
	for row in rows:
		row.db_update()


def set_service_costs_by_position(order):
	order.set_service_item_base_amounts()
	for item, service_item in zip(order.items, order.service_items, strict=False):
		item.service_cost_per_qty = service_item.base_amount / item.qty if item.qty else 0


def update_draft_receipts():
	receipt = frappe.qb.DocType("Subcontracting Receipt")
	receipt_item = frappe.qb.DocType("Subcontracting Receipt Item")
	order = frappe.qb.DocType("Subcontracting Order")
	order_item = frappe.qb.DocType("Subcontracting Order Item")
	service_costs = (
		frappe.qb.from_(receipt_item)
		.join(receipt)
		.on(receipt.name == receipt_item.parent)
		.join(order_item)
		.on(order_item.name == receipt_item.subcontracting_order_item)
		.join(order)
		.on(order.name == order_item.parent)
		.select(receipt_item.name, order_item.service_cost_per_qty)
		.where(
			(receipt.docstatus == 0)
			& (receipt.is_return == 0)
			& (order.conversion_rate != 1)
			& (receipt_item.service_cost_per_qty != order_item.service_cost_per_qty)
		)
		.run()
	)
	frappe.db.bulk_update(
		"Subcontracting Receipt Item",
		{name: {"service_cost_per_qty": cost} for name, cost in service_costs},
		update_modified=False,
	)
