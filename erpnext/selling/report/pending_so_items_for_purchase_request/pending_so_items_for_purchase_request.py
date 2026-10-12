# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.get("from_date") and filters.get("to_date") and filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Item Code"),
			"options": "Item",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"width": 200,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 140},
		{
			"label": _("S.O. No."),
			"options": "Sales Order",
			"fieldname": "sales_order_no",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 140},
		{
			"label": _("Material Request"),
			"fieldname": "material_request",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("Territory"), "fieldname": "territory", "fieldtype": "Data", "width": 140},
		{"label": _("SO Qty"), "fieldname": "so_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Requested Qty"), "fieldname": "requested_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Delivered Qty"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Pending Qty"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 140},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Data", "width": 140},
	]


def get_data(filters):
	permitted_orders = get_permitted_sales_orders(filters)
	if not permitted_orders:
		return []

	so = frappe.qb.DocType("Sales Order")
	so_item = frappe.qb.DocType("Sales Order Item")
	so_items = (
		frappe.qb.from_(so)
		.inner_join(so_item)
		.on(so.name == so_item.parent)
		.select(
			so_item.name.as_("so_item"),
			so_item.item_code,
			so_item.item_name,
			so_item.description,
			so_item.qty,
			so_item.delivered_qty,
			so.name.as_("sales_order"),
			so.transaction_date,
			so.customer,
			so.territory,
			so.company,
		)
		.where(so.name.isin(permitted_orders))
		.orderby(so.name, so_item.idx)
		.run(as_dict=1)
	)

	packed_item_map = get_packed_items(permitted_orders)
	requested_by_so_item, requested_by_packed_item, requested_by_item = get_requested_qty(permitted_orders)

	# a line is a bundle line when the order stored packed rows for it; this stays correct even if
	# the Product Bundle is later disabled, unlike checking the master
	groups = {}
	for row in so_items:
		packed_rows = packed_item_map.get((row.sales_order, row.so_item))
		if packed_rows:
			for packed in packed_rows:
				delivered = flt(row.delivered_qty) * (flt(packed.qty) / flt(row.qty)) if row.qty else 0
				linked = requested_by_packed_item.get(packed.name) or {}
				line = build_line(row, packed, flt(packed.qty), delivered, linked, is_packed=True)
				groups.setdefault((row.sales_order, packed.item_code), []).append(line)
		else:
			linked = requested_by_so_item.get(row.so_item) or {}
			line = build_line(row, row, flt(row.qty), flt(row.delivered_qty), linked, is_packed=False)
			groups.setdefault((row.sales_order, row.item_code), []).append(line)

	pending = []
	for key, lines in groups.items():
		# link-less requests (a duplicated or amended Material Request keeps only the Sales Order
		# link) are matched by item code and allocated across the group's lines once, packed first
		allocate_requests(pending, lines, requested_by_item.get(key) or {})

	return pending


def build_line(so_row, item_row, ordered_qty, delivered_qty, linked, is_packed):
	return frappe._dict(
		so_row=so_row,
		item_row=item_row,
		ordered_qty=ordered_qty,
		delivered_qty=delivered_qty,
		requested_qty=flt(linked.get("qty")),
		received_qty=flt(linked.get("received_qty")),
		material_requests=list(linked.get("material_requests", [])),
		is_packed=is_packed,
	)


def line_pending_qty(line):
	# mirror make_material_request's get_remaining_qty: goods received against a request already
	# cover that much delivery, so only delivery beyond the request reduces what is left to request
	return line.ordered_qty - line.requested_qty - max(line.delivered_qty - line.received_qty, 0)


def allocate_requests(pending, lines, bucket):
	bucket_qty = flt(bucket.get("qty"))
	bucket_received = flt(bucket.get("received_qty"))
	bucket_requests = list(bucket.get("material_requests", []))
	received_ratio = (bucket_received / bucket_qty) if bucket_qty else 0

	for line in sorted(lines, key=lambda line: not line.is_packed):
		pending_qty = line_pending_qty(line)
		if pending_qty <= 0:
			continue

		allocated = min(pending_qty, bucket_qty)
		if allocated > 0:
			bucket_qty -= allocated
			line.requested_qty += allocated
			line.received_qty += allocated * received_ratio
			line.material_requests += [mr for mr in bucket_requests if mr not in line.material_requests]
			pending_qty = line_pending_qty(line)

		if pending_qty > 0:
			add_pending_row(pending, line, pending_qty)


def add_pending_row(pending, line, pending_qty):
	pending.append(
		{
			"item_code": line.item_row.item_code,
			"item_name": line.item_row.item_name,
			"description": line.item_row.description,
			"sales_order_no": line.so_row.sales_order,
			"date": line.so_row.transaction_date,
			"material_request": ",".join(line.material_requests),
			"customer": line.so_row.customer,
			"territory": line.so_row.territory,
			"so_qty": line.ordered_qty,
			"requested_qty": line.requested_qty,
			"delivered_qty": line.delivered_qty,
			"pending_qty": pending_qty,
			"company": line.so_row.company,
		}
	)


def get_permitted_sales_orders(filters):
	so_filters = {
		"docstatus": 1,
		"status": ["not in", ["Closed", "Completed", "Cancelled"]],
	}

	if filters.get("company"):
		so_filters["company"] = filters.company
	if filters.get("customer"):
		so_filters["customer"] = filters.customer
	if filters.get("sales_order"):
		so_filters["name"] = filters.sales_order

	if filters.get("from_date") and filters.get("to_date"):
		so_filters["transaction_date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.get("from_date"):
		so_filters["transaction_date"] = [">=", filters.from_date]
	elif filters.get("to_date"):
		so_filters["transaction_date"] = ["<=", filters.to_date]

	# honours user permissions, which the raw query below bypasses
	return frappe.get_list("Sales Order", filters=so_filters, pluck="name", limit_page_length=0)


def get_requested_qty(sales_orders):
	# Material Request Item has no packed_item field on v15, so a bundle component's request
	# carries only the Sales Order link and is matched by item code (by_item)
	by_so_item = {}
	by_item = {}
	for mr in frappe.get_all(
		"Material Request Item",
		filters={"sales_order": ("in", sales_orders), "docstatus": 1},
		fields=["parent", "qty", "received_qty", "item_code", "sales_order", "sales_order_item"],
	):
		if mr.sales_order_item:
			target, key = by_so_item, mr.sales_order_item
		else:
			target, key = by_item, (mr.sales_order, mr.item_code)

		entry = target.setdefault(key, {"qty": 0, "received_qty": 0, "material_requests": []})
		entry["qty"] += flt(mr.qty)
		entry["received_qty"] += flt(mr.received_qty)
		if mr.parent not in entry["material_requests"]:
			entry["material_requests"].append(mr.parent)

	return by_so_item, {}, by_item


def get_packed_items(sales_orders):
	packed_item_map = {}
	for d in frappe.get_all(
		"Packed Item",
		filters={"parent": ("in", sales_orders)},
		fields=["name", "parent", "parent_detail_docname", "item_code", "item_name", "description", "qty"],
	):
		packed_item_map.setdefault((d.parent, d.parent_detail_docname), []).append(d)

	return packed_item_map
