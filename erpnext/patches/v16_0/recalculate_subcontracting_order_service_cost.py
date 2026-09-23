import frappe
from frappe.utils import flt

# Statuses that can still produce a Subcontracting Receipt.
PENDING_STATUSES = (
	"Draft",
	"Open",
	"Material Transferred",
	"Partial Material Transferred",
	"Partially Received",
)


def execute():
	orders = [
		order
		for order in frappe.get_all(
			"Subcontracting Order",
			filters={"docstatus": ["<", 2]},
			fields=["name", "purchase_order", "status"],
		)
		if order.purchase_order
	]
	if not orders:
		return

	conversion_rate_by_po = dict(
		frappe.get_all(
			"Purchase Order",
			filters={"name": ["in", list({order.purchase_order for order in orders})]},
			fields=["name", "conversion_rate"],
			as_list=True,
		)
	)
	conversion_rates = {
		order.name: flt(conversion_rate_by_po.get(order.purchase_order)) or 1.0 for order in orders
	}

	frappe.db.bulk_update(
		"Subcontracting Order",
		{name: {"conversion_rate": rate} for name, rate in conversion_rates.items()},
		update_modified=False,
	)

	service_items = frappe.get_all(
		"Subcontracting Order Service Item",
		filters={"parent": ["in", list(conversion_rates)]},
		fields=["name", "parent", "rate", "amount", "purchase_order_item"],
	)
	frappe.db.bulk_update(
		"Subcontracting Order Service Item",
		{
			service_item.name: {
				"base_rate": flt(service_item.rate) * conversion_rates[service_item.parent],
				"base_amount": flt(service_item.amount) * conversion_rates[service_item.parent],
			}
			for service_item in service_items
		},
		update_modified=False,
	)

	# Only orders that can still be received are recosted, so that receipts made from them stop
	# carrying the unconverted service cost. Completed orders keep the values their receipts used.
	pending = {
		order.name
		for order in orders
		if order.status in PENDING_STATUSES and conversion_rates[order.name] != 1.0
	}
	if not pending:
		return

	base_amounts = {
		(service_item.parent, service_item.purchase_order_item): flt(service_item.amount)
		* conversion_rates[service_item.parent]
		for service_item in service_items
		if service_item.parent in pending
	}

	item_updates = {}
	totals = {}
	for item in frappe.get_all(
		"Subcontracting Order Item",
		filters={"parent": ["in", list(pending)]},
		fields=[
			"name",
			"parent",
			"qty",
			"purchase_order_item",
			"rm_cost_per_qty",
			"additional_cost_per_qty",
		],
	):
		base_amount = base_amounts.get((item.parent, item.purchase_order_item), 0.0)
		service_cost_per_qty = base_amount / item.qty if item.qty else 0.0
		rate = flt(item.rm_cost_per_qty) + service_cost_per_qty + flt(item.additional_cost_per_qty)
		amount = flt(item.qty) * rate
		item_updates[item.name] = {
			"service_cost_per_qty": service_cost_per_qty,
			"rate": rate,
			"amount": amount,
		}
		totals[item.parent] = totals.get(item.parent, 0.0) + amount

	frappe.db.bulk_update("Subcontracting Order Item", item_updates, update_modified=False)
	frappe.db.bulk_update(
		"Subcontracting Order",
		{name: {"total": total} for name, total in totals.items()},
		update_modified=False,
	)
