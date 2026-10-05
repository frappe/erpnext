import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions
from frappe.utils import cint, escape_html, flt

from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_sre_reserved_qty_for_items_and_warehouses as get_reserved_stock_details,
)

QTY_FIELDS = (
	"projected_qty",
	"reserved_qty",
	"reserved_qty_for_production",
	"reserved_qty_for_sub_contract",
	"reserved_qty_for_production_plan",
	"reserved_stock",
	"ordered_qty",
	"indented_qty",
	"planned_qty",
	"actual_qty",
)


@frappe.whitelist()
def make_stock_entry(
	item_code: str,
	source_warehouse: str | None = None,
	target_warehouse: str | None = None,
	stock_entry_type: str | None = None,
	qty: float | None = None,
	rate: float | None = None,
):
	"""Return an unsaved Stock Entry for the item, with company taken from the warehouse"""
	stock_entry = frappe.new_doc("Stock Entry")
	if warehouse := source_warehouse or target_warehouse:
		stock_entry.company = frappe.get_cached_value("Warehouse", warehouse, "company")

	stock_entry.stock_entry_type = stock_entry_type or (
		"Material Transfer" if source_warehouse else "Material Receipt"
	)
	stock_entry.purpose = frappe.get_cached_value("Stock Entry Type", stock_entry.stock_entry_type, "purpose")
	stock_entry.from_warehouse = source_warehouse
	stock_entry.to_warehouse = target_warehouse

	stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")
	stock_entry.append(
		"items",
		{
			"item_code": item_code,
			"s_warehouse": source_warehouse,
			"t_warehouse": target_warehouse,
			"qty": flt(qty),
			"transfer_qty": flt(qty),
			"basic_rate": flt(rate),
			"uom": stock_uom,
			"stock_uom": stock_uom,
			"conversion_factor": 1,
		},
	)

	# checked against the doc so user permissions on company, warehouses and item apply;
	# generic message so values of restricted records are not leaked
	if not frappe.has_permission("Stock Entry", "create", doc=stock_entry):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	return stock_entry


@frappe.whitelist()
def get_data(
	item_code: str | None = None,
	warehouse: str | None = None,
	item_group: str | None = None,
	start: int = 0,
	sort_by: str = "actual_qty",
	sort_order: str = "desc",
):
	"""Return data to render the item dashboard"""
	if not frappe.has_permission("Bin", "read"):
		return []

	if sort_by not in QTY_FIELDS or sort_order not in ("asc", "desc"):
		frappe.throw(_("Invalid sort order"))

	filters = []
	if item_code:
		filters.append(["item_code", "=", item_code])
	if warehouse:
		filters.append(["warehouse", "=", warehouse])
	if item_group:
		lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])
		item = frappe.qb.DocType("Item")
		item_group_dt = frappe.qb.DocType("Item Group")
		items = (
			frappe.qb.from_(item)
			.select(item.name)
			.where(
				item.item_group.isin(
					frappe.qb.from_(item_group_dt)
					.select(item_group_dt.name)
					.where((item_group_dt.lft >= lft) & (item_group_dt.rgt <= rgt))
				)
			)
			.run(pluck="name")
		)
		filters.append(["item_code", "in", items])
	try:
		# check if user has any restrictions based on user permissions on warehouse
		if build_match_conditions("Warehouse", user=frappe.session.user):
			filters.append(["warehouse", "in", [w.name for w in frappe.get_list("Warehouse")]])
	except frappe.PermissionError:
		# user does not have access on warehouse; build_match_conditions already queued a
		# "Not permitted" message via frappe.throw before this was caught, drop it so the
		# client doesn't show a spurious error for a request that's failing gracefully here
		frappe.clear_last_message()
		return []

	items = frappe.db.get_all(
		"Bin",
		fields=[
			"item_code",
			"warehouse",
			"projected_qty",
			"reserved_qty",
			"reserved_qty_for_production",
			"reserved_qty_for_sub_contract",
			"actual_qty",
			"valuation_rate",
		],
		or_filters={field: ["!=", 0] for field in QTY_FIELDS},
		filters=filters,
		order_by=f"{sort_by} {sort_order}",
		limit_start=start,
		limit_page_length=21,
	)

	item_code_list = [item_code] if item_code else [i.item_code for i in items]
	warehouse_list = [warehouse] if warehouse else [i.warehouse for i in items]

	sre_reserved_stock_details = get_reserved_stock_details(item_code_list, warehouse_list)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

	for item in items:
		item.update(
			{
				"item_code": escape_html(item.item_code),
				"item_name": escape_html(frappe.get_cached_value("Item", item.item_code, "item_name")),
				"stock_uom": escape_html(frappe.get_cached_value("Item", item.item_code, "stock_uom")),
				"warehouse": escape_html(item.warehouse),
				"disable_quick_entry": frappe.get_cached_value("Item", item.item_code, "has_batch_no")
				or frappe.get_cached_value("Item", item.item_code, "has_serial_no"),
				"projected_qty": flt(item.projected_qty, precision),
				"reserved_qty": flt(item.reserved_qty, precision),
				"reserved_qty_for_production": flt(item.reserved_qty_for_production, precision),
				"reserved_qty_for_sub_contract": flt(item.reserved_qty_for_sub_contract, precision),
				"actual_qty": flt(item.actual_qty, precision),
				"reserved_stock": flt(sre_reserved_stock_details.get((item.item_code, item.warehouse))),
			}
		)

	return items
