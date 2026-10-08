import frappe
from frappe import _
from frappe.utils import create_batch, escape_html, flt

from erpnext.manufacturing.doctype.production_plan.production_plan import ProductionPlan


def execute():
	combined_plans = frappe.get_all(
		"Production Plan", filters={"docstatus": 1, "combine_items": 1}, pluck="name"
	)
	restore_sales_order_item_references(combined_plans)
	# Combined plans previously did not update Sales Order quantities.
	sales_orders = (
		frappe.get_all(
			"Production Plan Item Reference",
			filters={"docstatus": 1, "sales_order": ("is", "set"), "parent": ("in", combined_plans)},
			pluck="sales_order",
			distinct=True,
		)
		if combined_plans
		else []
	)
	# Older non-combined plans also added component units to their bundle parents.
	sales_orders += frappe.get_all(
		"Production Plan Item",
		filters={"docstatus": 1, "sales_order": ("is", "set"), "product_bundle_item": ("is", "set")},
		pluck="sales_order",
		distinct=True,
	)
	for batch in create_batch(sorted(set(sales_orders)), 500):
		quantities = ProductionPlan.get_so_wise_planned_qty(batch)
		items = frappe.get_all(
			"Sales Order Item", filters={"parent": ("in", batch)}, fields=["name", "parent"]
		)
		frappe.db.bulk_update(
			"Sales Order Item",
			{
				item.name: {"production_plan_qty": flt(quantities.get((item.parent, item.name)))}
				for item in items
			},
			update_modified=False,
		)


def restore_sales_order_item_references(combined_plans):
	if not combined_plans:
		return

	# The old Combine Items action could omit the Sales Order item names.
	references = frappe.get_all(
		"Production Plan Item Reference",
		filters={"docstatus": 1, "parent": ("in", combined_plans)},
		or_filters={"sales_order": ("is", "not set"), "sales_order_item": ("is", "not set")},
		fields=["name", "parent", "sales_order", "item_reference"],
	)
	by_plan = {}
	for row in references:
		by_plan.setdefault(row.parent, []).append(row)

	updates = {}
	unresolved = []
	for plan, rows in by_plan.items():
		plan_items = frappe.get_all(
			"Production Plan Item",
			filters={"parent": plan},
			fields=["item_code", "product_bundle_item", "sales_order_item"],
		)
		sales_orders = {row.sales_order for row in rows if row.sales_order}
		order_items = (
			frappe.get_all(
				"Sales Order Item",
				filters={"parent": ("in", sorted(sales_orders))},
				fields=["name", "parent", "item_code"],
			)
			if sales_orders
			else []
		)
		for row in rows:
			item_codes = {
				item.product_bundle_item or item.item_code
				for item in plan_items
				if not row.item_reference or item.sales_order_item == row.item_reference
			}
			matches = [
				item.name
				for item in order_items
				if item.parent == row.sales_order and item.item_code in item_codes
			]
			if len(matches) != 1:
				unresolved.append(plan)
				continue
			updates[row.name] = {"sales_order_item": matches[0]}

	if unresolved:
		frappe.throw(
			_(
				"Cannot rebuild planned quantities for Production Plans: {0}. "
				"Their missing Sales Order item references cannot be recovered unambiguously. "
				"Restore the references from the original orders or cancel the affected plans, then run migrate again."
			).format(", ".join(escape_html(plan) for plan in sorted(set(unresolved)))),
			title=_("Production Plan References Need Correction"),
		)
	if updates:
		frappe.db.bulk_update("Production Plan Item Reference", updates, update_modified=False)
