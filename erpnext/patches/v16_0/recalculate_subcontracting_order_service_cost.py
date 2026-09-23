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
	if not all(row.purchase_order_item for row in rows):
		return

	order.calculate_service_costs()
	order.calculate_items_qty_and_amount()
	order.db_update()
	for row in rows:
		row.db_update()
