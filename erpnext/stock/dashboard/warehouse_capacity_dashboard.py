import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions
from frappe.utils import cint, escape_html, flt, now_datetime


@frappe.whitelist()
def get_data(
	item_code: str | None = None,
	warehouse: str | None = None,
	parent_warehouse: str | None = None,
	company: str | None = None,
	start: int = 0,
	sort_by: str = "stock_capacity",
	sort_order: str = "desc",
):
	"""Return data to render the warehouse capacity dashboard."""
	frappe.has_permission("Item", "read", throw=True)
	frappe.has_permission("Putaway Rule", "read", throw=True)

	if sort_by not in ("stock_capacity", "actual_qty", "percent_occupied") or sort_order not in (
		"asc",
		"desc",
	):
		frappe.throw(_("Invalid sort order"))

	filters = get_filters(item_code, warehouse, parent_warehouse, company)

	no_permission, filters = get_warehouse_filter_based_on_permissions(filters)
	if no_permission:
		return []

	start = max(cint(start), 0)
	capacity_data = get_warehouse_capacity_data(filters, start, sort_by, sort_order)

	if sort_by != "stock_capacity":
		capacity_data.sort(key=lambda entry: entry[sort_by], reverse=sort_order == "desc")
		capacity_data = capacity_data[start : start + 11]

	return capacity_data


def get_filters(item_code=None, warehouse=None, parent_warehouse=None, company=None):
	filters = [["disable", "=", 0]]
	if item_code:
		filters.append(["item_code", "=", item_code])
	if warehouse:
		filters.append(["warehouse", "=", warehouse])
	if company:
		filters.append(["company", "=", company])
	if parent_warehouse:
		parent = frappe.get_doc("Warehouse", parent_warehouse)
		parent.check_permission("read")
		warehouses = frappe.get_list(
			"Warehouse",
			filters={"lft": [">=", parent.lft], "rgt": ["<=", parent.rgt]},
			pluck="name",
			limit_page_length=0,
		)
		filters.append(["warehouse", "in", warehouses])
	return filters


def get_warehouse_filter_based_on_permissions(filters):
	try:
		# check if user has any restrictions based on user permissions on warehouse
		if build_match_conditions("Warehouse", user=frappe.session.user):
			filters.append(
				["warehouse", "in", frappe.get_list("Warehouse", pluck="name", limit_page_length=0)]
			)
		return False, filters
	except frappe.PermissionError:
		# user does not have access on warehouse
		return True, []


def get_warehouse_capacity_data(filters, start, sort_by, sort_order):
	sort_by_capacity = sort_by == "stock_capacity"
	capacity_data = frappe.get_list(
		"Putaway Rule",
		fields=["name", "item_code", "warehouse", "stock_capacity", "company"],
		filters=filters,
		order_by=f"stock_capacity {sort_order}, name asc" if sort_by_capacity else "name asc",
		limit_start=start if sort_by_capacity else 0,
		limit_page_length=11 if sort_by_capacity else 0,
	)
	balances = get_stock_balances(capacity_data)

	for entry in capacity_data:
		balance_qty = balances.get(entry.pop("name")) or 0
		entry.update(
			{
				"warehouse": escape_html(entry.warehouse),
				"item_code": escape_html(entry.item_code),
				"company": escape_html(entry.company),
				"actual_qty": balance_qty,
				"percent_occupied": flt((flt(balance_qty) / flt(entry.stock_capacity)) * 100, 0),
			}
		)

	return capacity_data


def get_stock_balances(capacity_data):
	if not capacity_data:
		return {}

	rule = frappe.qb.DocType("Putaway Rule")
	ledger = frappe.qb.DocType("Stock Ledger Entry")
	latest_balance = (
		frappe.qb.from_(ledger)
		.select(ledger.qty_after_transaction)
		.where(
			(ledger.item_code == rule.item_code)
			& (ledger.warehouse == rule.warehouse)
			& (ledger.is_cancelled == 0)
			& (ledger.posting_datetime <= now_datetime())
		)
		.orderby(ledger.posting_datetime, order=frappe.qb.desc)
		.orderby(ledger.creation, order=frappe.qb.desc)
		.limit(1)
	)

	# Rule names come from the permission-filtered list above.
	return dict(
		frappe.qb.from_(rule)
		.select(rule.name, latest_balance.as_("actual_qty"))
		.where(rule.name.isin([entry.name for entry in capacity_data]))
		.run()
	)
