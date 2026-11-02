import frappe


def execute():
	company_currencies = dict(frappe.get_all("Company", fields=["name", "default_currency"], as_list=True))
	blanket_order_updates = {
		order.name: {
			"currency": company_currencies.get(order.company),
			"conversion_rate": 1.0,
		}
		for order in frappe.get_all("Blanket Order", fields=["name", "company", "currency"])
		if not order.currency
	}
	if blanket_order_updates:
		frappe.db.bulk_update("Blanket Order", blanket_order_updates, update_modified=False)

	item_updates = {
		item.name: {"base_rate": item.rate}
		for item in frappe.get_all("Blanket Order Item", fields=["name", "rate", "base_rate"])
		if not item.base_rate
	}
	if item_updates:
		frappe.db.bulk_update("Blanket Order Item", item_updates, update_modified=False)
