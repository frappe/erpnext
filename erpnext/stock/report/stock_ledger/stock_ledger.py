# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import copy

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, get_datetime

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import (
	get_inventory_dimensions,
	is_inventory_dimension_enabled,
)
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
from erpnext.stock.utils import (
	is_reposting_item_valuation_in_progress,
	update_included_uom_in_report,
)


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	include_uom = filters.get("include_uom")
	columns = get_columns(filters)
	items = get_items(filters)

	# Sub-ledger-backed inventory dimensions: filter by the matching bundles and read the dimension
	# split from the Inventory Dimension Entry sub-ledger instead of (now non-existent) SLE columns.
	# Skip entirely when the feature is disabled in Stock Settings.
	dimension_enabled = is_inventory_dimension_enabled()
	dimension_filter, dimension_display = ({}, {})
	dimension_contributions, dimension_bundles = {}, None
	if dimension_enabled:
		dimension_filter, dimension_display = get_dimension_sub_ledger_filter(filters)
		if dimension_filter:
			dimension_contributions, dimension_bundles = get_dimension_bundle_contributions(
				filters, dimension_filter, items
			)

	sl_entries = get_stock_ledger_entries(filters, items, bundles=dimension_bundles)
	item_details = get_item_details(items, sl_entries, include_uom)

	# When the report is not already filtered by a dimension, still show each row's dimension
	# value(s) from its bundle so the dimension columns aren't blank.
	if dimension_enabled and not dimension_filter:
		set_sub_ledger_dimension_values(sl_entries)

	inv_dimension_key = []
	inv_dimension_wise_value = get_inv_dimension_wise_value(filters)
	if inv_dimension_wise_value:
		for key in inv_dimension_wise_value:
			value = inv_dimension_wise_value[key]
			if isinstance(value, list):
				inv_dimension_key.extend(value)
			else:
				inv_dimension_key.append(value)

	if filters.get("batch_no"):
		opening_row = get_opening_balance_from_batch(filters, columns, sl_entries)
	elif dimension_filter:
		opening_row = get_sub_ledger_dimension_opening(filters, dimension_filter, dimension_display)
	elif inv_dimension_wise_value:
		opening_row = get_opening_balance_for_inv_dimension(filters, inv_dimension_wise_value)
	else:
		opening_row = get_opening_balance(filters, columns, sl_entries, inv_dimension_wise_value)

	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
	bundle_details = {}

	if filters.get("segregate_serial_batch_bundle"):
		bundle_details = get_serial_batch_bundle_details(sl_entries, filters)

	data = []
	conversion_factors = []
	if opening_row:
		data.append(opening_row)
		conversion_factors.append(0)

	actual_qty = stock_value = 0
	if opening_row:
		actual_qty = opening_row.get("qty_after_transaction")
		stock_value = opening_row.get("stock_value")

	available_serial_nos = {}

	batch_balance_dict = frappe._dict({})
	if actual_qty and filters.get("batch_no"):
		batch_balance_dict[filters.batch_no] = [actual_qty, stock_value]

	inv_dimension_wise_dict = frappe._dict({})
	set_opening_row_for_inv_dimension(
		inv_dimension_wise_dict, filters, inv_dimension_key=inv_dimension_key, opening_row=opening_row
	)

	# Running balance per (item_code, warehouse) for the dimension-filtered path. An opening row only
	# exists for a single item+warehouse combination; seed that combination from it.
	dimension_running = {}
	opening_item_codes = as_filter_list(filters.get("item_code"))
	opening_warehouses = as_filter_list(filters.get("warehouse"))
	if opening_row and len(opening_item_codes) == 1 and len(opening_warehouses) == 1:
		dimension_running[(opening_item_codes[0], opening_warehouses[0])] = {
			"qty": flt(opening_row.get("qty_after_transaction")),
			"value": flt(opening_row.get("stock_value")),
		}

	item_wh_wise_prev_sle = {}
	for sle in sl_entries:
		item_detail = item_details[sle.item_code]

		sle.update(item_detail)

		if dimension_filter:
			apply_sub_ledger_dimension(sle, dimension_contributions, dimension_display, dimension_running)
			data.append(sle)
			if include_uom:
				conversion_factors.append(item_detail.conversion_factor)
			continue

		if bundle_info := bundle_details.get(sle.serial_and_batch_bundle):
			data.extend(get_segregated_bundle_entries(sle, bundle_info, batch_balance_dict, filters))
			continue

		if inv_dimension_key:
			set_balance_value_for_inv_dimesion(inv_dimension_key, inv_dimension_wise_dict, sle)

		if filters.get("batch_no"):
			actual_qty += flt(sle.actual_qty, precision)
			stock_value += sle.stock_value_difference
			if sle.batch_no:
				if not batch_balance_dict.get(sle.batch_no):
					batch_balance_dict[sle.batch_no] = [0, 0]

				batch_balance_dict[sle.batch_no][0] += sle.actual_qty
				batch_balance_dict[sle.batch_no][1] += stock_value

			if filters.get("segregate_serial_batch_bundle"):
				actual_qty = batch_balance_dict[sle.batch_no][0]

			if sle.voucher_type == "Stock Reconciliation" and not sle.actual_qty:
				actual_qty = sle.qty_after_transaction
				stock_value = sle.stock_value

			sle.update({"qty_after_transaction": actual_qty, "stock_value": stock_value})

		sle.update({"in_qty": max(sle.actual_qty, 0), "out_qty": min(sle.actual_qty, 0)})

		if sle.serial_no:
			update_available_serial_nos(available_serial_nos, sle)

		if sle.actual_qty < 0:
			sle["in_out_rate"] = flt(sle.stock_value_difference / sle.actual_qty, precision)
			sle["incoming_rate"] = 0

		elif sle.voucher_type == "Stock Reconciliation" and sle.actual_qty < 0:
			sle["in_out_rate"] = sle.valuation_rate

		if (
			sle.voucher_type == "Stock Reconciliation"
			and not sle.in_qty
			and not sle.out_qty
			and not sle.actual_qty
		):
			if prev_sle := item_wh_wise_prev_sle.get((sle.item_code, sle.warehouse)):
				bal_qty = prev_sle.get("qty_after_transaction", 0)
				qty = sle.qty_after_transaction - bal_qty
				if qty > 0:
					sle.in_qty = qty
				elif qty < 0:
					sle.out_qty = qty

		item_wh_wise_prev_sle[(sle.item_code, sle.warehouse)] = sle
		data.append(sle)

		if include_uom:
			conversion_factors.append(item_detail.conversion_factor)

	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
	return columns, data


def set_opening_row_for_inv_dimension(
	inv_dimension_wise_dict, filters, inv_dimension_key=None, opening_row=None
):
	if (
		not inv_dimension_key
		or not opening_row
		or not filters.get("item_code")
		or not filters.get("warehouse")
	):
		return

	if len(filters.get("item_code")) > 1 or len(filters.get("warehouse")) > 1:
		return

	if inv_dimension_key and opening_row and filters.get("item_code") and filters.get("warehouse"):
		new_key = copy.deepcopy(inv_dimension_key)
		new_key.extend([filters.item_code[0], filters.warehouse[0]])

		opening_key = tuple(new_key)
		inv_dimension_wise_dict[opening_key] = {
			"qty_after_transaction": flt(opening_row.get("qty_after_transaction")),
			"dimension_stock_value": flt(opening_row.get("stock_value")),
		}


def set_balance_value_for_inv_dimesion(inv_dimension_key, inv_dimension_wise_dict, sle):
	new_key = copy.deepcopy(inv_dimension_key)
	new_key.extend([sle.item_code, sle.warehouse])
	new_key = tuple(new_key)

	if new_key not in inv_dimension_wise_dict:
		inv_dimension_wise_dict[new_key] = {"qty_after_transaction": 0, "dimension_stock_value": 0}

	inv_dimesion_value = inv_dimension_wise_dict[new_key]
	inv_dimesion_value["qty_after_transaction"] += sle.actual_qty
	inv_dimesion_value["dimension_stock_value"] += sle.stock_value_difference
	sle.update(
		{
			"qty_after_transaction": inv_dimesion_value["qty_after_transaction"],
			"stock_value": inv_dimesion_value["dimension_stock_value"],
		}
	)


def get_segregated_bundle_entries(sle, bundle_details, batch_balance_dict, filters):
	segregated_entries = []
	qty_before_transaction = sle.qty_after_transaction - sle.actual_qty
	stock_value_before_transaction = sle.stock_value - sle.stock_value_difference

	for row in bundle_details:
		new_sle = copy.deepcopy(sle)
		new_sle.update(row)
		new_sle.update(
			{
				"in_out_rate": flt(new_sle.stock_value_difference / row.qty) if row.qty < 0 else 0,
				"in_qty": row.qty if row.qty > 0 else 0,
				"out_qty": row.qty if row.qty < 0 else 0,
				"qty_after_transaction": qty_before_transaction + row.qty,
				"stock_value": stock_value_before_transaction + new_sle.stock_value_difference,
				"incoming_rate": row.incoming_rate if row.qty > 0 else 0,
			}
		)

		if filters.get("batch_no") and row.batch_no:
			if not batch_balance_dict.get(row.batch_no):
				batch_balance_dict[row.batch_no] = [0, 0]

			batch_balance_dict[row.batch_no][0] += row.qty
			batch_balance_dict[row.batch_no][1] += row.stock_value_difference

			new_sle.update(
				{
					"qty_after_transaction": batch_balance_dict[row.batch_no][0],
					"stock_value": batch_balance_dict[row.batch_no][1],
				}
			)

		qty_before_transaction += row.qty
		stock_value_before_transaction += new_sle.stock_value_difference

		new_sle.valuation_rate = (
			stock_value_before_transaction / qty_before_transaction if qty_before_transaction else 0
		)

		segregated_entries.append(new_sle)

	return segregated_entries


def get_serial_batch_bundle_details(sl_entries, filters=None):
	bundle_details = []
	for sle in sl_entries:
		if sle.serial_and_batch_bundle:
			bundle_details.append(sle.serial_and_batch_bundle)

	if not bundle_details:
		return frappe._dict({})

	query_filers = {"parent": ("in", bundle_details)}
	if filters.get("batch_no"):
		query_filers["batch_no"] = filters.batch_no

	_bundle_details = frappe._dict({})
	batch_entries = frappe.get_all(
		"Serial and Batch Entry",
		filters=query_filers,
		fields=["parent", "qty", "incoming_rate", "stock_value_difference", "batch_no", "serial_no"],
		order_by="parent, idx",
	)
	for entry in batch_entries:
		_bundle_details.setdefault(entry.parent, []).append(entry)

	return _bundle_details


def update_available_serial_nos(available_serial_nos, sle):
	serial_nos = get_serial_nos(sle.serial_no)
	key = (sle.item_code, sle.warehouse)
	if key not in available_serial_nos:
		stock_balance = get_stock_balance_for(
			sle.item_code, sle.warehouse, sle.posting_date, sle.posting_time
		)
		serials = get_serial_nos(stock_balance["serial_nos"]) if stock_balance["serial_nos"] else []
		available_serial_nos.setdefault(key, serials)

	existing_serial_no = available_serial_nos[key]
	for sn in serial_nos:
		if sle.actual_qty > 0:
			if sn in existing_serial_no:
				existing_serial_no.remove(sn)
			else:
				existing_serial_no.append(sn)
		else:
			if sn in existing_serial_no:
				existing_serial_no.remove(sn)
			else:
				existing_serial_no.append(sn)

	sle.balance_serial_no = "\n".join(existing_serial_no)


def get_columns(filters):
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 100},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
	]

	for dimension in get_inventory_dimensions():
		columns.append(
			{
				"label": _(dimension.doctype),
				"fieldname": dimension.fieldname,
				"fieldtype": "Link",
				"options": dimension.doctype,
				"width": 110,
			}
		)

	columns.extend(
		[
			{
				"label": _("In Qty"),
				"fieldname": "in_qty",
				"fieldtype": "Float",
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Out Qty"),
				"fieldname": "out_qty",
				"fieldtype": "Float",
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Balance Qty"),
				"fieldname": "qty_after_transaction",
				"fieldtype": "Float",
				"width": 100,
				"convertible": "qty",
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 150,
			},
			{
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
			{
				"label": _("Brand"),
				"fieldname": "brand",
				"fieldtype": "Link",
				"options": "Brand",
				"width": 100,
			},
			{"label": _("Description"), "fieldname": "description", "width": 200},
			{
				"label": _("Incoming Rate"),
				"fieldname": "incoming_rate",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
				"convertible": "rate",
			},
			{
				"label": _("Avg Rate (Balance Stock)"),
				"fieldname": "valuation_rate",
				"fieldtype": filters.valuation_field_type,
				"width": 180,
				"options": "Company:company:default_currency"
				if filters.valuation_field_type == "Currency"
				else None,
				"convertible": "rate",
			},
			{
				"label": _("Outgoing Rate"),
				"fieldname": "in_out_rate",
				"fieldtype": filters.valuation_field_type,
				"width": 140,
				"options": "Company:company:default_currency"
				if filters.valuation_field_type == "Currency"
				else None,
				"convertible": "rate",
			},
			{
				"label": _("Balance Value"),
				"fieldname": "stock_value",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
			},
			{
				"label": _("Value Change"),
				"fieldname": "stock_value_difference",
				"fieldtype": "Currency",
				"width": 110,
				"options": "Company:company:default_currency",
			},
			{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 110},
			{
				"label": _("Voucher #"),
				"fieldname": "voucher_no",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 100,
			},
			{
				"label": _("Serial and Batch Bundle"),
				"fieldname": "serial_and_batch_bundle",
				"fieldtype": "Link",
				"options": "Serial and Batch Bundle",
				"width": 150,
				"hidden": not filters.get("segregate_serial_batch_bundle"),
			},
			{
				"label": _("Batch"),
				"fieldname": "batch_no",
				"fieldtype": "Link",
				"options": "Batch",
				"width": 100,
				"hidden": not filters.get("segregate_serial_batch_bundle"),
			},
			{
				"label": _("Serial No"),
				"fieldname": "serial_no",
				"fieldtype": "Link",
				"options": "Serial No",
				"width": 100,
				"hidden": not filters.get("segregate_serial_batch_bundle"),
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100,
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 110,
			},
		]
	)

	return columns


def get_stock_ledger_entries(filters, items, bundles=None):
	from_date = get_datetime(filters.from_date + " 00:00:00")
	to_date = get_datetime(filters.to_date + " 23:59:59")

	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			sle.posting_datetime.as_("date"),
			sle.warehouse,
			sle.posting_date,
			sle.posting_time,
			sle.actual_qty,
			sle.incoming_rate,
			sle.valuation_rate,
			sle.company,
			sle.voucher_type,
			sle.qty_after_transaction,
			sle.stock_value_difference,
			sle.serial_and_batch_bundle,
			sle.inventory_dimension_bundle,
			sle.voucher_no,
			sle.stock_value,
			sle.batch_no,
			sle.serial_no,
			sle.project,
		)
		.where((sle.docstatus < 2) & (sle.is_cancelled == 0) & (sle.posting_datetime[from_date:to_date]))
		.orderby(sle.posting_datetime)
		.orderby(sle.creation)
	)

	inventory_dimension_fields = get_inventory_dimension_fields()
	if inventory_dimension_fields:
		for fieldname in inventory_dimension_fields:
			query = query.select(fieldname)
			if fieldname in filters and filters.get(fieldname):
				query = query.where(sle[fieldname].isin(filters.get(fieldname)))

	# Sub-ledger-backed dimensions are filtered by the matching bundles (the dimension value is no
	# longer a column on Stock Ledger Entry); an empty set means nothing matched the dimension.
	if bundles is not None:
		if not bundles:
			return []
		query = query.where(sle.inventory_dimension_bundle.isin(list(bundles)))

	if items:
		query = query.where(sle.item_code.isin(items))

	for field in ["voucher_no", "project", "company"]:
		if filters.get(field) and field not in inventory_dimension_fields:
			query = query.where(sle[field] == filters.get(field))

	if filters.get("batch_no"):
		bundles = get_serial_and_batch_bundles(filters)

		if bundles:
			query = query.where(
				(sle.serial_and_batch_bundle.isin(bundles)) | (sle.batch_no == filters.batch_no)
			)
		else:
			query = query.where(sle.batch_no == filters.batch_no)

	query = apply_warehouse_filter(query, sle, filters)

	return query.run(as_dict=True)


def get_serial_and_batch_bundles(filters):
	SBB = frappe.qb.DocType("Serial and Batch Bundle")
	SBE = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(SBE)
		.inner_join(SBB)
		.on(SBE.parent == SBB.name)
		.select(SBE.parent)
		.where(
			(SBB.docstatus == 1)
			& (SBB.has_batch_no == 1)
			& (SBB.voucher_no.notnull())
			& (SBE.batch_no == filters.batch_no)
		)
	)

	return query.run(pluck=SBE.parent)


def get_inventory_dimension_fields():
	# Inventory dimensions are stored in the qty-only sub-ledger now. A dimension that has a
	# sub-ledger column (Inventory Dimension Entry) is read from there, not from Stock Ledger Entry,
	# even if the legacy SLE column still physically exists (it is left as an unpopulated orphan).
	# Only a truly legacy dimension - one with an SLE column but no sub-ledger column - uses this path.
	return [
		dimension.fieldname
		for dimension in get_inventory_dimensions()
		if frappe.db.has_column("Stock Ledger Entry", dimension.fieldname)
		and not frappe.db.has_column("Inventory Dimension Entry", dimension.source_fieldname)
	]


def get_items(filters):
	item = frappe.qb.DocType("Item")
	query = frappe.qb.from_(item).select(item.name)
	conditions = []

	if item_codes := filters.get("item_code"):
		conditions.append(item.name.isin(item_codes))

	else:
		if brand := filters.get("brand"):
			conditions.append(item.brand == brand)

		if filters.get("item_group") and (
			condition := get_item_group_condition(filters.get("item_group"), item)
		):
			conditions.append(condition)

	items = []
	if conditions:
		for condition in conditions:
			query = query.where(condition)

		items = [r[0] for r in query.run()]

	return items


def get_item_details(items, sl_entries, include_uom):
	item_details = {}
	if not items:
		items = list(set(d.item_code for d in sl_entries))

	if not items:
		return item_details

	item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(item)
		.select(item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom)
		.where(item.name.isin(items))
	)

	if include_uom:
		ucd = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			query.left_join(ucd)
			.on((ucd.parent == item.name) & (ucd.uom == include_uom))
			.select(ucd.conversion_factor)
		)

	res = query.run(as_dict=True)

	for item in res:
		item_details.setdefault(item.name, item)

	return item_details


# TODO: THIS IS NOT USED
def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("project=%(project)s")

	for dimension in get_inventory_dimensions():
		if filters.get(dimension.fieldname):
			conditions.append(f"{dimension.fieldname} in %({dimension.fieldname})s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_opening_balance_from_batch(filters, columns, sl_entries):
	query_filters = {
		"batch_no": filters.batch_no,
		"docstatus": 1,
		"is_cancelled": 0,
		"posting_date": ("<", filters.from_date),
		"company": filters.company,
	}

	for fields in ["item_code", "warehouse"]:
		if value := filters.get(fields):
			query_filters[fields] = ("in", value)

	opening_data = frappe.get_all(
		"Stock Ledger Entry",
		fields=[
			{"SUM": "actual_qty", "as": "qty_after_transaction"},
			{"SUM": "stock_value_difference", "as": "stock_value"},
		],
		filters=query_filters,
	)[0]

	for field in ["qty_after_transaction", "stock_value", "valuation_rate"]:
		if opening_data.get(field) is None:
			opening_data[field] = 0.0

	table = frappe.qb.DocType("Stock Ledger Entry")
	sabb_table = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(table)
		.inner_join(sabb_table)
		.on(table.serial_and_batch_bundle == sabb_table.parent)
		.select(
			Sum(sabb_table.qty).as_("qty"),
			Sum(sabb_table.stock_value_difference).as_("stock_value"),
		)
		.where(
			(sabb_table.batch_no == filters.batch_no)
			& (sabb_table.docstatus == 1)
			& (table.posting_date < filters.from_date)
			& (table.is_cancelled == 0)
		)
	)

	for field in ["item_code", "warehouse", "company"]:
		value = filters.get(field)

		if not value:
			continue

		if isinstance(value, list | tuple):
			query = query.where(table[field].isin(value))

		else:
			query = query.where(table[field] == value)

	bundle_data = query.run(as_dict=True)

	if bundle_data:
		opening_data.qty_after_transaction += flt(bundle_data[0].qty)
		opening_data.stock_value += flt(bundle_data[0].stock_value)
		if opening_data.qty_after_transaction:
			opening_data.valuation_rate = flt(opening_data.stock_value) / flt(
				opening_data.qty_after_transaction
			)

	return {
		"item_code": _("'Opening'"),
		"qty_after_transaction": opening_data.qty_after_transaction,
		"valuation_rate": opening_data.valuation_rate,
		"stock_value": opening_data.stock_value,
	}


def get_opening_balance(filters, columns, sl_entries, inv_dimension_wise_value=None):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle

	project = None
	if filters.get("project") and not frappe.get_all(
		"Inventory Dimension", filters={"reference_document": "Project"}
	):
		project = filters.get("project")

	last_entry = get_previous_sle(
		{
			"item_code": filters.item_code,
			"warehouse_condition": get_warehouse_condition(filters.warehouse),
			"posting_date": filters.from_date,
			"posting_time": "00:00:00",
			"project": project,
		},
		for_report=True,
	)

	# check if any SLEs are actually Opening Stock Reconciliation
	for sle in list(sl_entries):
		if (
			sle.get("voucher_type") == "Stock Reconciliation"
			and sle.posting_date == filters.from_date
			and frappe.db.get_value("Stock Reconciliation", sle.voucher_no, "purpose") == "Opening Stock"
		):
			last_entry = sle
			sl_entries.remove(sle)

	row = {
		"item_code": _("'Opening'"),
		"qty_after_transaction": last_entry.get("qty_after_transaction", 0),
		"valuation_rate": last_entry.get("valuation_rate", 0),
		"stock_value": last_entry.get("stock_value", 0),
	}

	return row


def get_warehouse_condition(warehouses):
	if not warehouses:
		return ""

	if isinstance(warehouses, str):
		warehouses = [warehouses]

	warehouse_range = frappe.get_all(
		"Warehouse",
		filters={
			"name": ("in", warehouses),
		},
		fields=["lft", "rgt"],
		as_list=True,
	)

	if not warehouse_range:
		return ""

	alias = "wh"
	conditions = []
	for lft, rgt in warehouse_range:
		conditions.append(f"({alias}.lft >= {lft} and {alias}.rgt <= {rgt})")

	conditions = " or ".join(conditions)

	return f" exists (select name from `tabWarehouse` {alias} \
		where ({conditions}) and warehouse = {alias}.name)"


def get_item_group_condition(item_group, item_table=None):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		if item_table:
			ig = frappe.qb.DocType("Item Group")
			return item_table.item_group.isin(
				frappe.qb.from_(ig)
				.select(ig.name)
				.where(
					(ig.lft >= item_group_details.lft)
					& (ig.rgt <= item_group_details.rgt)
					& (item_table.item_group == ig.name)
				)
			)
		else:
			return f"item.item_group in (select ig.name from `tabItem Group` ig \
				where ig.lft >= {item_group_details.lft} and ig.rgt <= {item_group_details.rgt} and item.item_group = ig.name)"


def get_opening_balance_for_inv_dimension(filters, inv_dimension_wise_value):
	if not filters.item_code or not filters.warehouse or not filters.from_date:
		return

	if len(filters.get("item_code")) > 1 or len(filters.get("warehouse")) > 1:
		return

	sl_doctype = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sl_doctype)
		.select(
			sl_doctype.item_code,
			sl_doctype.warehouse,
			Sum(sl_doctype.actual_qty).as_("qty_after_transaction"),
			Sum(sl_doctype.stock_value_difference).as_("stock_value"),
		)
		.where(
			(sl_doctype.posting_date < filters.from_date)
			& (sl_doctype.docstatus < 2)
			& (sl_doctype.is_cancelled == 0)
		)
	)

	if filters.get("item_code"):
		if isinstance(filters.item_code, list | tuple):
			query = query.where(sl_doctype.item_code.isin(filters.item_code))
		else:
			query = query.where(sl_doctype.item_code == filters.item_code)

	if filters.get("warehouse"):
		if isinstance(filters.warehouse, list | tuple):
			query = query.where(sl_doctype.warehouse.isin(filters.warehouse))
		else:
			query = query.where(sl_doctype.warehouse == filters.warehouse)

	for key, value in inv_dimension_wise_value.items():
		if isinstance(value, list | tuple):
			query = query.where(sl_doctype[key].isin(value))
		else:
			query = query.where(sl_doctype[key] == value)

	query = query.groupby(sl_doctype.item_code, sl_doctype.warehouse)

	opening_data = query.run(as_dict=True)

	if opening_data:
		return frappe._dict(
			{
				"item_code": _("'Opening'"),
				"qty_after_transaction": opening_data[0].qty_after_transaction,
				"stock_value": opening_data[0].stock_value,
				"valuation_rate": flt(opening_data[0].stock_value)
				/ flt(opening_data[0].qty_after_transaction)
				if opening_data[0].qty_after_transaction
				else 0,
			}
		)

	return frappe._dict({})


def get_inv_dimension_wise_value(filters) -> list:
	inv_dimension_key = frappe._dict({})
	for dimension in get_inventory_dimensions():
		# Sub-ledger-backed dimensions are handled separately via the Inventory Dimension Entry
		# sub-ledger; only truly legacy column-backed dimensions (SLE column, no sub-ledger column)
		# use this running-balance path.
		if (
			dimension.fieldname in filters
			and filters.get(dimension.fieldname)
			and frappe.db.has_column("Stock Ledger Entry", dimension.fieldname)
			and not frappe.db.has_column("Inventory Dimension Entry", dimension.source_fieldname)
		):
			inv_dimension_key[dimension.fieldname] = filters.get(dimension.fieldname)

	if filters.get("project") and not frappe.get_all(
		"Inventory Dimension", filters={"reference_document": "Project"}
	):
		inv_dimension_key["project"] = filters.get("project")

	return inv_dimension_key


def get_dimension_sub_ledger_filter(filters):
	"""Dimensions the user filtered on that are backed by the Inventory Dimension Entry sub-ledger.

	Returns ``({source_fieldname: value}, {report_column_fieldname: display_value})``. The first drives
	the sub-ledger query; the second sets the dimension column on each row for display.
	"""
	entry_doctype = "Inventory Dimension Entry"
	source_values, display_map = {}, {}
	for dimension in get_inventory_dimensions():
		target, source = dimension.fieldname, dimension.source_fieldname
		if not source or not filters.get(target) or not frappe.db.has_column(entry_doctype, source):
			continue

		source_values[source] = filters.get(target)
		value = filters.get(target)
		display_map[target] = value[0] if isinstance(value, list | tuple) else value

	return source_values, display_map


def set_sub_ledger_dimension_values(sl_entries):
	"""Populate each SLE row's inventory-dimension columns from its bundle's sub-ledger entries.

	A bundle may split a row's qty across several dimension values; they are shown comma-separated.
	"""
	entry_doctype = "Inventory Dimension Entry"
	dimensions = [
		frappe._dict(source=dimension.source_fieldname, target=dimension.fieldname)
		for dimension in get_inventory_dimensions()
		if dimension.source_fieldname and frappe.db.has_column(entry_doctype, dimension.source_fieldname)
	]
	if not dimensions:
		return

	bundles = {
		sle.get("inventory_dimension_bundle") for sle in sl_entries if sle.get("inventory_dimension_bundle")
	}
	if not bundles:
		return

	entry = frappe.qb.DocType(entry_doctype)
	query = (
		frappe.qb.from_(entry)
		.select(entry.parent, *[entry[dimension.source] for dimension in dimensions])
		.where((entry.parent.isin(list(bundles))) & (entry.is_cancelled == 0))
	)

	values_by_bundle = {}
	for row in query.run(as_dict=True):
		bucket = values_by_bundle.setdefault(
			row.parent, {dimension.target: set() for dimension in dimensions}
		)
		for dimension in dimensions:
			if row.get(dimension.source):
				bucket[dimension.target].add(row.get(dimension.source))

	for sle in sl_entries:
		bucket = values_by_bundle.get(sle.get("inventory_dimension_bundle"))
		if not bucket:
			continue

		for target, values in bucket.items():
			if values:
				sle[target] = ", ".join(sorted(values))


def _apply_dimension_filter(query, entry, source_values):
	for source, value in source_values.items():
		if isinstance(value, list | tuple):
			query = query.where(entry[source].isin(value))
		else:
			query = query.where(entry[source] == value)
	return query


def get_dimension_bundle_contributions(filters, source_values, items):
	"""Net qty each bundle contributes to the filtered dimension, keyed by ``(bundle, warehouse)``.

	Also returns the set of bundles touching the dimension so the SLE query can be restricted to them.
	"""
	entry = frappe.qb.DocType("Inventory Dimension Entry")
	bundle = frappe.qb.DocType("Inventory Dimension Bundle")

	query = (
		frappe.qb.from_(entry)
		.join(bundle)
		.on(entry.parent == bundle.name)
		.select(
			entry.parent.as_("bundle"),
			entry.warehouse,
			entry.qty,
		)
		.where((entry.is_cancelled == 0) & (entry.docstatus == 1))
	)
	query = _apply_dimension_filter(query, entry, source_values)

	if items:
		query = query.where(entry.item_code.isin(items))
	if filters.get("warehouse"):
		query = query.where(entry.warehouse.isin(filters.get("warehouse")))
	if filters.get("company"):
		query = query.where(bundle.company == filters.get("company"))

	contributions, bundles = {}, set()
	for row in query.run(as_dict=True):
		bundles.add(row.bundle)
		# Inventory Dimension Entry qty is stored signed (negative for outward).
		signed_qty = flt(row.qty)
		contributions[(row.bundle, row.warehouse)] = (
			contributions.get((row.bundle, row.warehouse), 0.0) + signed_qty
		)

	return contributions, bundles


def as_filter_list(value) -> list:
	"""Normalise a filter value (scalar or list) to a list so ``[0]``/``len`` are safe.

	The report passes item_code/warehouse as MultiSelectLists, but the function may also be called
	with a scalar string; ``len("ITEM-001") > 1`` would otherwise misfire.
	"""
	if not value:
		return []
	return list(value) if isinstance(value, list | tuple) else [value]


def get_sub_ledger_dimension_opening(filters, source_values, display_map):
	"""Opening row for the filtered dimension, computed from the sub-ledger before ``from_date``."""
	item_codes = as_filter_list(filters.get("item_code"))
	warehouses = as_filter_list(filters.get("warehouse"))
	if not item_codes or not warehouses or not filters.get("from_date"):
		return

	if len(item_codes) > 1 or len(warehouses) > 1:
		return

	item_code, warehouse = item_codes[0], warehouses[0]
	entry = frappe.qb.DocType("Inventory Dimension Entry")
	bundle = frappe.qb.DocType("Inventory Dimension Bundle")
	from_datetime = get_datetime(filters.from_date + " 00:00:00")

	query = (
		frappe.qb.from_(entry)
		.join(bundle)
		.on(entry.parent == bundle.name)
		.select(entry.qty)
		.where(
			(entry.is_cancelled == 0)
			& (entry.docstatus == 1)
			& (entry.item_code == item_code)
			& (entry.warehouse == warehouse)
			& (entry.posting_datetime < from_datetime)
		)
	)
	query = _apply_dimension_filter(query, entry, source_values)
	if filters.get("company"):
		query = query.where(bundle.company == filters.get("company"))

	# Inventory Dimension Entry qty is stored signed (negative for outward).
	opening_qty = sum(flt(row.qty) for row in query.run(as_dict=True))
	if not opening_qty:
		return

	rate = get_valuation_rate_before(item_code, warehouse, filters.from_date)
	opening_row = frappe._dict(
		{
			"item_code": _("'Opening'"),
			"qty_after_transaction": opening_qty,
			"stock_value": opening_qty * rate,
			"valuation_rate": rate,
		}
	)
	opening_row.update(display_map)
	return opening_row


def get_valuation_rate_before(item_code, warehouse, from_date):
	"""Valuation rate of the last Stock Ledger Entry for the item/warehouse before ``from_date``."""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	rate = (
		frappe.qb.from_(sle)
		.select(sle.valuation_rate)
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.is_cancelled == 0)
			& (sle.posting_date < from_date)
		)
		.orderby(sle.posting_datetime, order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
		.limit(1)
	).run()

	return flt(rate[0][0]) if rate else 0.0


def apply_sub_ledger_dimension(sle, contributions, display_map, running):
	"""Override an SLE row with the filtered dimension's qty/value and running balance.

	The running balance is tracked per ``(item_code, warehouse)`` so a dimension filter spanning
	multiple items/warehouses does not produce a meaningless combined balance.
	"""
	dim_qty = flt(contributions.get((sle.get("inventory_dimension_bundle"), sle.warehouse), 0.0))
	valuation_rate = flt(sle.valuation_rate)
	dim_value = dim_qty * valuation_rate

	balance = running.setdefault((sle.item_code, sle.warehouse), {"qty": 0.0, "value": 0.0})
	balance["qty"] += dim_qty
	balance["value"] += dim_value

	sle.actual_qty = dim_qty
	sle.stock_value_difference = dim_value
	sle.update({"in_qty": max(dim_qty, 0), "out_qty": min(dim_qty, 0)})
	sle.qty_after_transaction = balance["qty"]
	sle.stock_value = balance["value"]
	sle.incoming_rate = valuation_rate if dim_qty > 0 else 0
	sle.in_out_rate = valuation_rate
	sle.update(display_map)
