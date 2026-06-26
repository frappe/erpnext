# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cstr, flt, now, nowdate, nowtime

from erpnext.controllers.stock_controller import create_repost_item_valuation_entry


def repost(only_actual=False, allow_negative_stock=False, allow_zero_rate=False, only_bin=False):
	"""
	Repost everything!
	"""
	frappe.db.auto_commit_on_many_writes = 1

	if allow_negative_stock:
		existing_allow_negative_stock = frappe.get_single_value("Stock Settings", "allow_negative_stock")
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

	item_warehouses = frappe.get_all("Bin", fields=["item_code", "warehouse"], as_list=True)
	item_warehouses += frappe.get_all(
		"Stock Ledger Entry", fields=["item_code", "warehouse"], distinct=True, as_list=True
	)
	item_warehouses = list({tuple(d) for d in item_warehouses})
	for d in item_warehouses:
		try:
			repost_stock(d[0], d[1], allow_zero_rate, only_actual, only_bin, allow_negative_stock)
			if not frappe.in_test:
				frappe.db.commit()
		except Exception:
			frappe.db.rollback()

	if allow_negative_stock:
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", existing_allow_negative_stock)
	frappe.db.auto_commit_on_many_writes = 0


def repost_stock(
	item_code,
	warehouse,
	allow_zero_rate=False,
	only_actual=False,
	only_bin=False,
	allow_negative_stock=False,
):
	if not only_bin:
		repost_actual_qty(item_code, warehouse, allow_zero_rate, allow_negative_stock)

	if item_code and warehouse and not only_actual:
		qty_dict = {
			"reserved_qty": get_reserved_qty(item_code, warehouse),
			"indented_qty": get_indented_qty(item_code, warehouse),
			"ordered_qty": get_ordered_qty(item_code, warehouse),
			"planned_qty": get_planned_qty(item_code, warehouse),
		}
		if only_bin:
			qty_dict.update({"actual_qty": get_balance_qty_from_sle(item_code, warehouse)})

		update_bin_qty(item_code, warehouse, qty_dict)


def repost_actual_qty(item_code, warehouse, allow_zero_rate=False, allow_negative_stock=False):
	create_repost_item_valuation_entry(
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"posting_date": "1900-01-01",
			"posting_time": "00:01",
			"allow_negative_stock": allow_negative_stock,
			"allow_zero_rate": allow_zero_rate,
		}
	)


def get_balance_qty_from_sle(item_code, warehouse):
	balance_qty = frappe.get_all(
		"Stock Ledger Entry",
		filters={"item_code": item_code, "warehouse": warehouse, "is_cancelled": 0},
		fields=["qty_after_transaction"],
		order_by="posting_datetime desc, creation desc",
		limit=1,
	)

	return flt(balance_qty[0].qty_after_transaction) if balance_qty else 0.0


def get_reserved_qty(item_code, warehouse):
	dont_reserve_on_return = frappe.get_cached_value(
		"Selling Settings", "Selling Settings", "dont_reserve_sales_order_qty_on_sales_return"
	)
	so = frappe.qb.DocType("Sales Order")
	so_item = frappe.qb.DocType("Sales Order Item")
	packed_item = frappe.qb.DocType("Packed Item")

	open_so = (so.docstatus == 1) & so.status.notin(["On Hold", "Closed"])
	not_delivered_by_supplier = so_item.delivered_by_supplier.isnull() | (so_item.delivered_by_supplier == 0)

	# Keep the reserved-qty rollup in the DB (one aggregate per branch) instead of streaming
	# every open packed-item / SO-item row into Python. `qty <> 0` mirrors the original
	# `where so_item_qty >= so_item_delivered_qty` *and* guards the divide-by-`qty` below
	# (MariaDB returned NULL for x/0, postgres raises), so qty=0 rows -- which contributed
	# nothing anyway -- are excluded on both databases.
	reservable = (so_item.qty != 0) & (so_item.qty >= so_item.delivered_qty)
	if dont_reserve_on_return:
		net_reserved = so_item.qty - so_item.delivered_qty - so_item.returned_qty
	else:
		net_reserved = so_item.qty - so_item.delivered_qty

	# Bundled (packed) items reserving stock against an open Sales Order
	packed_qty = (
		frappe.qb.from_(packed_item)
		.inner_join(so)
		.on(so.name == packed_item.parent)
		.inner_join(so_item)
		.on(so_item.name == packed_item.parent_detail_docname)
		.select(Sum(packed_item.qty * net_reserved / so_item.qty))
		.where(
			(packed_item.item_code == item_code)
			& (packed_item.warehouse == warehouse)
			& (packed_item.parenttype == "Sales Order")
			& (packed_item.item_code != packed_item.parent_item)
			& not_delivered_by_supplier
			& open_so
			& reservable
		)
		.run()
	)

	# Sales Order items directly reserving stock
	so_item_qty = (
		frappe.qb.from_(so_item)
		.inner_join(so)
		.on(so.name == so_item.parent)
		.select(Sum(so_item.stock_qty * net_reserved / so_item.qty))
		.where(
			(so_item.item_code == item_code)
			& (so_item.warehouse == warehouse)
			& not_delivered_by_supplier
			& open_so
			& reservable
		)
		.run()
	)

	return flt(packed_qty[0][0]) + flt(so_item_qty[0][0])


def get_indented_qty(item_code, warehouse):
	# Ordered Qty is always maintained in stock UOM
	mr_item = frappe.qb.DocType("Material Request Item")
	mr = frappe.qb.DocType("Material Request")
	base_conditions = (
		(mr_item.item_code == item_code)
		& (mr_item.warehouse == warehouse)
		& (mr_item.stock_qty > mr_item.ordered_qty)
		& (mr.status != "Stopped")
		& (mr.docstatus == 1)
	)

	inward_qty = (
		frappe.qb.from_(mr_item)
		.inner_join(mr)
		.on(mr_item.parent == mr.name)
		.select(Sum(mr_item.stock_qty - mr_item.ordered_qty))
		.where(
			base_conditions
			& mr.material_request_type.isin(
				["Purchase", "Manufacture", "Customer Provided", "Material Transfer"]
			)
		)
		.run()
	)
	inward_qty = flt(inward_qty[0][0]) if inward_qty else 0

	outward_qty = (
		frappe.qb.from_(mr_item)
		.inner_join(mr)
		.on(mr_item.parent == mr.name)
		.select(Sum(mr_item.stock_qty - mr_item.ordered_qty))
		.where(base_conditions & (mr.material_request_type == "Material Issue"))
		.run()
	)
	outward_qty = flt(outward_qty[0][0]) if outward_qty else 0

	requested_qty = inward_qty - outward_qty

	return requested_qty


def get_ordered_qty(item_code, warehouse):
	"""Return total pending ordered quantity for an item in a warehouse.
	Includes outstanding quantities from Purchase Orders and Subcontracting Orders"""

	purchase_order_qty = get_purchase_order_qty(item_code, warehouse)
	subcontracting_order_qty = get_subcontracting_order_qty(item_code, warehouse)

	return flt(purchase_order_qty) + flt(subcontracting_order_qty)


def get_purchase_order_qty(item_code, warehouse):
	PurchaseOrder = frappe.qb.DocType("Purchase Order")
	PurchaseOrderItem = frappe.qb.DocType("Purchase Order Item")

	purchase_order_qty = (
		frappe.qb.from_(PurchaseOrderItem)
		.join(PurchaseOrder)
		.on(PurchaseOrderItem.parent == PurchaseOrder.name)
		.select(
			Sum(
				(PurchaseOrderItem.qty - PurchaseOrderItem.received_qty) * PurchaseOrderItem.conversion_factor
			)
		)
		.where(
			(PurchaseOrderItem.item_code == item_code)
			& (PurchaseOrderItem.warehouse == warehouse)
			& (PurchaseOrderItem.qty > PurchaseOrderItem.received_qty)
			& (PurchaseOrder.status.notin(["Closed", "Delivered"]))
			& (PurchaseOrder.docstatus == 1)
			& (Coalesce(PurchaseOrderItem.delivered_by_supplier, 0) == 0)
		)
		.run()
	)

	return purchase_order_qty[0][0] if purchase_order_qty else 0


def get_subcontracting_order_qty(item_code, warehouse):
	SubcontractingOrder = frappe.qb.DocType("Subcontracting Order")
	SubcontractingOrderItem = frappe.qb.DocType("Subcontracting Order Item")

	subcontracting_order_qty = (
		frappe.qb.from_(SubcontractingOrderItem)
		.join(SubcontractingOrder)
		.on(SubcontractingOrderItem.parent == SubcontractingOrder.name)
		.select(
			Sum(
				(SubcontractingOrderItem.qty - SubcontractingOrderItem.received_qty)
				* SubcontractingOrderItem.conversion_factor
			)
		)
		.where(
			(SubcontractingOrderItem.item_code == item_code)
			& (SubcontractingOrderItem.warehouse == warehouse)
			& (SubcontractingOrderItem.qty > SubcontractingOrderItem.received_qty)
			& (SubcontractingOrder.status.notin(["Closed", "Completed"]))
			& (SubcontractingOrder.docstatus == 1)
		)
		.run()
	)

	return subcontracting_order_qty[0][0] if subcontracting_order_qty else 0


def get_planned_qty(item_code, warehouse):
	wo = frappe.qb.DocType("Work Order")
	planned_qty = (
		frappe.qb.from_(wo)
		.select(Sum(wo.qty - wo.produced_qty))
		.where(
			(wo.production_item == item_code)
			& (wo.fg_warehouse == warehouse)
			& wo.status.notin(["Stopped", "Completed", "Closed"])
			& (wo.docstatus == 1)
			& (wo.qty > wo.produced_qty)
		)
		.run()
	)

	return flt(planned_qty[0][0]) if planned_qty else 0


def update_bin_qty(item_code, warehouse, qty_dict=None):
	from erpnext.stock.utils import get_bin

	bin = get_bin(item_code, warehouse)
	mismatch = False
	for field, value in qty_dict.items():
		if flt(bin.get(field)) != flt(value):
			bin.set(field, flt(value))
			mismatch = True

	bin.modified = now()
	if mismatch:
		bin.set_projected_qty()
		bin.db_update()
		bin.clear_cache()


def set_stock_balance_as_per_serial_no(
	item_code=None, posting_date=None, posting_time=None, fiscal_year=None
):
	if not posting_date:
		posting_date = nowdate()
	if not posting_time:
		posting_time = nowtime()

	bin_dt = frappe.qb.DocType("Bin")
	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(bin_dt)
		.inner_join(item)
		.on(bin_dt.item_code == item.name)
		.select(bin_dt.item_code, bin_dt.warehouse, bin_dt.actual_qty, item.stock_uom)
		.where(item.has_serial_no == 1)
	)
	if item_code:
		query = query.where(item.name == item_code)
	bin = query.run()

	for d in bin:
		serial_nos = frappe.db.count(
			"Serial No", {"item_code": d[0], "warehouse": d[1], "docstatus": ["<", 2]}
		)

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": d[0], "warehouse": d[1], "is_cancelled": 0},
			fields=["valuation_rate", "company"],
			# total order so the latest SLE is picked identically on both engines (was posting_date only)
			order_by="posting_date desc, creation desc, name desc",
			limit=1,
			as_list=True,
		)

		sle_dict = {
			"doctype": "Stock Ledger Entry",
			"item_code": d[0],
			"warehouse": d[1],
			"transaction_date": nowdate(),
			"posting_date": posting_date,
			"posting_time": posting_time,
			"voucher_type": "Stock Reconciliation (Manual)",
			"voucher_no": "",
			"voucher_detail_no": "",
			"actual_qty": flt(serial_nos) - flt(d[2]),
			"stock_uom": d[3],
			"incoming_rate": sle and flt(serial_nos) > flt(d[2]) and flt(sle[0][0]) or 0,
			"company": sle and cstr(sle[0][1]) or 0,
			"batch_no": "",
			"serial_no": "",
		}

		sle_doc = frappe.get_doc(sle_dict)
		sle_doc.flags.ignore_validate = True
		sle_doc.flags.ignore_links = True
		sle_doc.insert()

		args = sle_dict.copy()
		args.update({"sle_id": sle_doc.name})

		create_repost_item_valuation_entry(
			{
				"item_code": d[0],
				"warehouse": d[1],
				"posting_date": posting_date,
				"posting_time": posting_time,
			}
		)
