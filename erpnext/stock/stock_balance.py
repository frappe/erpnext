# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import cstr, flt, now, nowdate, nowtime

from erpnext.controllers.stock_controller import create_repost_item_valuation_entry


def repost(only_actual=False, allow_negative_stock=False, allow_zero_rate=False, only_bin=False):
	"""
	Repost everything!
	"""
	frappe.db.auto_commit_on_many_writes = 1

	if allow_negative_stock:
		existing_allow_negative_stock = frappe.db.get_value("Stock Settings", None, "allow_negative_stock")
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

	item_warehouses = frappe.db.sql(
		"""
		select distinct item_code, warehouse
		from
			(select item_code, warehouse from tabBin
			union
			select item_code, warehouse from `tabStock Ledger Entry`) a
	"""
	)
	for d in item_warehouses:
		try:
			repost_stock(d[0], d[1], allow_zero_rate, only_actual, only_bin, allow_negative_stock)
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
	balance_qty = frappe.db.sql(
		"""select qty_after_transaction from `tabStock Ledger Entry`
		where item_code=%s and warehouse=%s and is_cancelled=0
		order by posting_datetime desc, creation desc
		limit 1""",
		(item_code, warehouse),
	)

	return flt(balance_qty[0][0]) if balance_qty else 0.0


def get_reserved_qty(item_code, warehouse):
	dont_reserve_on_return = frappe.get_cached_value(
		"Selling Settings", "Selling Settings", "dont_reserve_sales_order_qty_on_sales_return"
	)
	reserved_qty = frappe.db.sql(
		f"""
		select
			sum(dnpi_qty * ((so_item_qty - so_item_delivered_qty - if(dont_reserve_qty_on_return, so_item_returned_qty, 0)) / so_item_qty))
		from
			(
				(select
					qty as dnpi_qty,
					(
						select qty from `tabSales Order Item`
						where name = dnpi.parent_detail_docname
						and (delivered_by_supplier is null or delivered_by_supplier = 0)
					) as so_item_qty,
					(
						select delivered_qty from `tabSales Order Item`
						where name = dnpi.parent_detail_docname
						and delivered_by_supplier = 0
					) as so_item_delivered_qty,
					(
						select returned_qty from `tabSales Order Item`
						where name = dnpi.parent_detail_docname
						and delivered_by_supplier = 0
					) as so_item_returned_qty,
					{dont_reserve_on_return} as dont_reserve_qty_on_return,
					parent, name
				from
				(
					select qty, parent_detail_docname, parent, name
					from `tabPacked Item` dnpi_in
					where item_code = %s and warehouse = %s
					and parenttype='Sales Order'
					and item_code != parent_item
					and exists (select * from `tabSales Order` so
					where name = dnpi_in.parent and docstatus = 1 and status not in ('On Hold', 'Closed'))
				) dnpi)
			union
				(select stock_qty as dnpi_qty, qty as so_item_qty,
					delivered_qty as so_item_delivered_qty,
					returned_qty as so_item_returned_qty,
					{dont_reserve_on_return}, parent, name
				from `tabSales Order Item` so_item
				where item_code = %s and warehouse = %s
				and (so_item.delivered_by_supplier is null or so_item.delivered_by_supplier = 0)
				and exists(select * from `tabSales Order` so
					where so.name = so_item.parent and so.docstatus = 1
					and so.status not in ('On Hold', 'Closed')))
			) tab
		where
			so_item_qty >= so_item_delivered_qty
	""",
		(item_code, warehouse, item_code, warehouse),
	)

	return flt(reserved_qty[0][0]) if reserved_qty else 0


def get_indented_qty(item_code, warehouse):
	# Ordered Qty is always maintained in stock UOM
	inward_qty = frappe.db.sql(
		"""
		select sum(mr_item.stock_qty - mr_item.ordered_qty)
		from `tabMaterial Request Item` mr_item, `tabMaterial Request` mr
		where mr_item.item_code=%s and mr_item.warehouse=%s
			and mr.material_request_type in ('Purchase', 'Manufacture', 'Customer Provided', 'Material Transfer')
			and mr_item.stock_qty > mr_item.ordered_qty and mr_item.parent=mr.name
			and mr.status!='Stopped' and mr.docstatus=1
	""",
		(item_code, warehouse),
	)
	inward_qty = flt(inward_qty[0][0]) if inward_qty else 0

	outward_qty = frappe.db.sql(
		"""
		select sum(mr_item.stock_qty - mr_item.ordered_qty)
		from `tabMaterial Request Item` mr_item, `tabMaterial Request` mr
		where mr_item.item_code=%s and mr_item.warehouse=%s
			and mr.material_request_type = 'Material Issue'
			and mr_item.stock_qty > mr_item.ordered_qty and mr_item.parent=mr.name
			and mr.status!='Stopped' and mr.docstatus=1
	""",
		(item_code, warehouse),
	)
	outward_qty = flt(outward_qty[0][0]) if outward_qty else 0

	requested_qty = inward_qty - outward_qty

	return requested_qty


def get_ordered_qty(item_code, warehouse):
	ordered_qty = frappe.db.sql(
		"""
		select sum((po_item.qty - po_item.received_qty)*po_item.conversion_factor)
		from `tabPurchase Order Item` po_item, `tabPurchase Order` po
		where po_item.item_code=%s and po_item.warehouse=%s
		and po_item.qty > po_item.received_qty and po_item.parent=po.name
		and po.status not in ('Closed', 'Delivered') and po.docstatus=1
		and po_item.delivered_by_supplier = 0""",
		(item_code, warehouse),
	)

	return flt(ordered_qty[0][0]) if ordered_qty else 0


def get_planned_qty(item_code, warehouse):
	planned_qty = frappe.db.sql(
		"""
		select sum(qty - produced_qty) from `tabWork Order`
		where production_item = %s and fg_warehouse = %s and status not in ('Stopped', 'Completed', 'Closed')
		and docstatus=1 and qty > produced_qty""",
		(item_code, warehouse),
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

	condition = " and item.name='%s'" % item_code.replace("'", "'") if item_code else ""

	bin = frappe.db.sql(
		"""select bin.item_code, bin.warehouse, bin.actual_qty, item.stock_uom
		from `tabBin` bin, tabItem item
		where bin.item_code = item.name and item.has_serial_no = 1 %s"""
		% condition
	)

	for d in bin:
		serial_nos = frappe.db.sql(
			"""select count(name) from `tabSerial No`
			where item_code=%s and warehouse=%s and docstatus < 2""",
			(d[0], d[1]),
		)

		sle = frappe.db.sql(
			"""select valuation_rate, company from `tabStock Ledger Entry`
			where item_code = %s and warehouse = %s and is_cancelled = 0
			order by posting_date desc limit 1""",
			(d[0], d[1]),
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
			"actual_qty": flt(serial_nos[0][0]) - flt(d[2]),
			"stock_uom": d[3],
			"incoming_rate": sle and flt(serial_nos[0][0]) > flt(d[2]) and flt(sle[0][0]) or 0,
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
