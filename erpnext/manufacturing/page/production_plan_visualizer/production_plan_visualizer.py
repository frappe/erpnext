import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt


@frappe.whitelist()
def get_plan_overview(production_plan: str):
	plan = frappe.get_doc("Production Plan", production_plan)
	plan.check_permission("read")

	work_orders = get_work_orders(production_plan)
	purchase_orders = get_purchase_orders(production_plan)
	schedule = get_schedule(production_plan)

	return {
		"plan": get_plan_details(plan),
		"finished_goods": get_finished_goods(plan, work_orders),
		"sub_assemblies": get_sub_assemblies(plan, work_orders, purchase_orders),
		"material_requests": get_material_requests(production_plan),
		"materials": get_materials(plan, production_plan),
		"schedule": schedule,
		"row_materials": get_row_materials(plan, schedule),
	}


def get_materials(plan, production_plan):
	raised = {}
	for row in get_raised_material_request_items(production_plan):
		raised.setdefault(row.material_request_plan_item, []).append(row)

	stock = get_stock_levels(plan)
	return [build_material(row, raised.get(row.name) or [], stock) for row in plan.mr_items]


def get_stock_levels(plan):
	items = {row.item_code for row in plan.mr_items}
	warehouses = {row.warehouse for row in plan.mr_items if row.warehouse}
	if not items or not warehouses:
		return {}

	bins = frappe.get_all(
		"Bin",
		filters={"item_code": ("in", items), "warehouse": ("in", warehouses)},
		fields=["item_code", "warehouse", "actual_qty", "projected_qty"],
	)

	return {(d.item_code, d.warehouse): d for d in bins}


def build_material(row, raised, stock):
	documents = {
		entry.name: {"doctype": "Material Request", "name": entry.name, "status": entry.status}
		for entry in raised
	}
	level = stock.get((row.item_code, row.warehouse)) or frappe._dict()

	return {
		"row_name": row.name,
		"item_code": row.item_code,
		"item_name": row.item_name,
		"uom": row.uom,
		"warehouse": row.warehouse,
		"material_request_type": row.material_request_type,
		"required_qty": flt(row.required_bom_qty) or flt(row.quantity),
		"to_procure_qty": flt(row.quantity),
		"available_qty": flt(level.actual_qty) if level else flt(row.actual_qty),
		"projected_qty": flt(level.projected_qty) if level else flt(row.projected_qty),
		"requested_qty": flt(row.requested_qty),
		"ordered_qty": sum(flt(entry.ordered_qty) for entry in raised),
		"received_qty": sum(flt(entry.received_qty) for entry in raised),
		"schedule_date": row.schedule_date,
		"consumer": row.get("sub_assembly_item_reference"),
		"main_item_code": row.get("main_item_code"),
		"documents": list(documents.values()),
	}


def get_raised_material_request_items(production_plan):
	if not frappe.has_permission("Material Request"):
		return []

	mr_item = frappe.qb.DocType("Material Request Item")
	material_request = frappe.qb.DocType("Material Request")

	return (
		frappe.qb.from_(mr_item)
		.inner_join(material_request)
		.on(mr_item.parent == material_request.name)
		.select(
			mr_item.parent.as_("name"),
			mr_item.material_request_plan_item,
			mr_item.item_code,
			mr_item.qty,
			mr_item.ordered_qty,
			mr_item.received_qty,
			material_request.status,
		)
		.where((mr_item.production_plan == production_plan) & (mr_item.docstatus < 2))
		.orderby(material_request.transaction_date)
		.run(as_dict=True)
	)


def get_row_materials(plan, schedule):
	material_items = {d.item_code for d in schedule if d.row_type == "Raw Material"}
	material_items.update(row.item_code for row in plan.mr_items)
	rows = [(d.name, d.bom_no) for d in plan.po_items + plan.sub_assembly_items if d.bom_no]
	if not material_items or not rows:
		return {}

	bom_items = frappe.get_all(
		"BOM Item",
		filters={
			"parent": ("in", {bom_no for _, bom_no in rows}),
			"parenttype": "BOM",
			"item_code": ("in", material_items),
		},
		fields=["parent", "item_code"],
	)

	by_bom = {}
	for d in bom_items:
		by_bom.setdefault(d.parent, []).append(d.item_code)

	return {name: by_bom[bom_no] for name, bom_no in rows if by_bom.get(bom_no)}


def get_plan_details(plan):
	total_planned = flt(plan.total_planned_qty)
	total_produced = flt(plan.total_produced_qty)
	return {
		"name": plan.name,
		"status": plan.status,
		"docstatus": plan.docstatus,
		"company": plan.company,
		"posting_date": plan.posting_date,
		"total_planned_qty": total_planned,
		"total_produced_qty": total_produced,
		"completion": flt(total_produced / total_planned * 100 if total_planned else 0, 1),
	}


def get_finished_goods(plan, work_orders):
	rows = []
	for row in plan.po_items:
		documents = [d for d in work_orders if d.production_plan_item == row.name]
		produced_qty = sum(flt(d.produced_qty) for d in documents)
		rows.append(
			{
				"row_name": row.name,
				"item_code": row.item_code,
				"item_name": frappe.get_cached_value("Item", row.item_code, "item_name"),
				"sales_order": row.get("sales_order"),
				"warehouse": row.warehouse,
				"planned_start_date": row.planned_start_date,
				"planned_end_date": row.get("planned_end_date"),
				"qty": flt(row.planned_qty),
				"produced_qty": produced_qty,
				"pending_qty": flt(row.planned_qty) - produced_qty,
				"stock_uom": row.stock_uom,
				"documents": documents,
			}
		)

	return rows


def get_sub_assemblies(plan, work_orders, purchase_orders):
	rows = []
	for item in plan.sub_assembly_items:
		if item.type_of_manufacturing == "Subcontract":
			documents = [d for d in purchase_orders if d.production_plan_sub_assembly_item == item.name]
		else:
			documents = [d for d in work_orders if d.production_plan_sub_assembly_item == item.name]

		produced_qty = sum(flt(d.produced_qty) for d in documents)
		rows.append(
			{
				"row_name": item.name,
				"production_plan_item": item.production_plan_item,
				"item_code": item.production_item,
				"item_name": item.item_name,
				"qty": flt(item.qty),
				"produced_qty": produced_qty,
				"pending_qty": flt(item.qty) - produced_qty,
				"available_qty": flt(item.actual_qty),
				"bom_level": item.bom_level,
				"indent": item.indent or 0,
				"type_of_manufacturing": item.type_of_manufacturing,
				"supplier": item.get("supplier"),
				"schedule_date": item.schedule_date,
				"uom": item.stock_uom or item.uom,
				"documents": documents,
			}
		)

	return rows


def get_work_orders(production_plan):
	if not frappe.has_permission("Work Order"):
		return []

	work_orders = frappe.get_list(
		"Work Order",
		filters={"production_plan": production_plan, "docstatus": ("<", 2)},
		fields=[
			"name",
			"qty",
			"produced_qty",
			"material_transferred_for_manufacturing",
			"status",
			"docstatus",
			"planned_start_date",
			"production_item as item_code",
			"item_name",
			"production_plan_item",
			"production_plan_sub_assembly_item",
		],
		order_by="creation",
		limit_page_length=0,
	)

	for row in work_orders:
		row.doctype = "Work Order"

	return work_orders


def get_purchase_orders(production_plan):
	if not frappe.has_permission("Purchase Order"):
		return []

	po_item = frappe.qb.DocType("Purchase Order Item")
	purchase_order = frappe.qb.DocType("Purchase Order")

	purchase_orders = (
		frappe.qb.from_(po_item)
		.inner_join(purchase_order)
		.on(po_item.parent == purchase_order.name)
		.select(
			po_item.parent.as_("name"),
			po_item.qty.as_("order_qty"),
			po_item.received_qty,
			po_item.fg_item,
			po_item.fg_item_qty,
			po_item.production_plan_sub_assembly_item,
			purchase_order.status,
			purchase_order.docstatus,
			purchase_order.supplier,
		)
		.where((po_item.production_plan == production_plan) & (po_item.docstatus < 2))
		.run(as_dict=True)
	)

	for row in purchase_orders:
		row.doctype = "Purchase Order"
		row.qty = flt(row.fg_item_qty) if row.fg_item else flt(row.order_qty)
		row.produced_qty = flt(row.received_qty)
		if row.fg_item:
			row.produced_qty = flt(row.received_qty) / (flt(row.order_qty) / flt(row.fg_item_qty) or 1)

	return purchase_orders


def get_material_requests(production_plan):
	if not frappe.has_permission("Material Request"):
		return []

	mr_item = frappe.qb.DocType("Material Request Item")
	material_request = frappe.qb.DocType("Material Request")

	return (
		frappe.qb.from_(mr_item)
		.inner_join(material_request)
		.on(mr_item.parent == material_request.name)
		.select(
			mr_item.parent.as_("name"),
			material_request.status,
			material_request.material_request_type,
			material_request.transaction_date,
			material_request.per_ordered,
			material_request.per_received,
			Sum(mr_item.qty).as_("qty"),
		)
		.where((mr_item.production_plan == production_plan) & (mr_item.docstatus < 2))
		.groupby(
			mr_item.parent,
			material_request.status,
			material_request.material_request_type,
			material_request.transaction_date,
			material_request.per_ordered,
			material_request.per_received,
		)
		.orderby(material_request.transaction_date)
		.run(as_dict=True)
	)


def get_schedule(production_plan):
	if not frappe.has_permission("Production Plan Schedule"):
		return []

	return frappe.get_list(
		"Production Plan Schedule",
		filters={"production_plan": production_plan},
		fields=[
			"name",
			"subject",
			"row_type",
			"plan_row",
			"item_code",
			"item_name",
			"operation",
			"workstation",
			"supplier",
			"from_time",
			"to_time",
			"duration_mins",
		],
		order_by="from_time",
		limit_page_length=0,
	)
