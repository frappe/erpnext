# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime, IfNull, Sum
from frappe.utils import cstr, flt, get_link_to_form, get_time, getdate, nowdate, nowtime

import erpnext
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_available_serial_nos,
)
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses
from erpnext.stock.serial_batch_bundle import BatchNoValuation, SerialNoValuation
from erpnext.stock.valuation import FIFOValuation, LIFOValuation

BarcodeScanResult = dict[str, str | None]


class InvalidWarehouseCompany(frappe.ValidationError):
	pass


class PendingRepostingError(frappe.ValidationError):
	pass


def get_stock_value_from_bin(warehouse=None, item_code=None):
	values = {}
	conditions = ""
	if warehouse:
		conditions += """ and `tabBin`.warehouse in (
						select w2.name from `tabWarehouse` w1
						join `tabWarehouse` w2 on
						w1.name = %(warehouse)s
						and w2.lft between w1.lft and w1.rgt
						) """

		values["warehouse"] = warehouse

	if item_code:
		conditions += " and `tabBin`.item_code = %(item_code)s"

		values["item_code"] = item_code

	query = (
		"""select sum(stock_value) from `tabBin`, `tabItem` where 1 = 1
		and `tabItem`.name = `tabBin`.item_code and ifnull(`tabItem`.disabled, 0) = 0 %s"""
		% conditions
	)

	stock_value = frappe.db.sql(query, values)

	return stock_value


def get_stock_value_on(
	warehouses: list | str | None = None, posting_date: str | None = None, item_code: str | None = None
) -> float:
	if not posting_date:
		posting_date = nowdate()

	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(IfNull(Sum(sle.stock_value_difference), 0))
		.where((sle.posting_date <= posting_date) & (sle.is_cancelled == 0))
	)

	if warehouses:
		if isinstance(warehouses, str):
			warehouses = [warehouses]

		warehouses = set(warehouses)
		for wh in list(warehouses):
			if frappe.db.get_value("Warehouse", wh, "is_group"):
				warehouses.update(get_child_warehouses(wh))

		query = query.where(sle.warehouse.isin(warehouses))

	if item_code:
		query = query.where(sle.item_code == item_code)

	return query.run(as_list=True)[0][0]


@frappe.whitelist()
def get_stock_balance(
	item_code,
	warehouse,
	posting_date=None,
	posting_time=None,
	with_valuation_rate=False,
	with_serial_no=False,
	inventory_dimensions_dict=None,
):
	"""Returns stock balance quantity at given warehouse on given posting date or current date.

	If `with_valuation_rate` is True, will return tuple (qty, rate)"""

	from erpnext.stock.stock_ledger import get_previous_sle

	if posting_date is None:
		posting_date = nowdate()
	if posting_time is None:
		posting_time = nowtime()

	args = {
		"item_code": item_code,
		"warehouse": warehouse,
		"posting_date": posting_date,
		"posting_time": posting_time,
	}

	extra_cond = ""
	if inventory_dimensions_dict:
		for field, value in inventory_dimensions_dict.items():
			args[field] = value
			extra_cond += f" and {field} = %({field})s"

	last_entry = get_previous_sle(args, extra_cond=extra_cond)

	if with_valuation_rate:
		if with_serial_no:
			serial_no_details = get_available_serial_nos(
				frappe._dict(
					{
						"item_code": item_code,
						"warehouse": warehouse,
						"posting_date": posting_date,
						"posting_time": posting_time,
						"ignore_warehouse": 1,
					}
				)
			)

			serial_nos = ""
			if serial_no_details:
				serial_nos = "\n".join(d.serial_no for d in serial_no_details)

			return (
				(last_entry.qty_after_transaction, last_entry.valuation_rate, serial_nos)
				if last_entry
				else (0.0, 0.0, None)
			)
		else:
			return (last_entry.qty_after_transaction, last_entry.valuation_rate) if last_entry else (0.0, 0.0)
	else:
		return last_entry.qty_after_transaction if last_entry else 0.0


def get_serial_nos_data(serial_nos):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	return get_serial_nos(serial_nos)


@frappe.whitelist()
def get_latest_stock_qty(item_code, warehouse=None):
	values, condition = [item_code], ""
	if warehouse:
		lft, rgt, is_group = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt", "is_group"])

		if is_group:
			values.extend([lft, rgt])
			condition += "and exists (\
				select name from `tabWarehouse` wh where wh.name = tabBin.warehouse\
				and wh.lft >= %s and wh.rgt <= %s)"

		else:
			values.append(warehouse)
			condition += " AND warehouse = %s"

	actual_qty = frappe.db.sql(
		f"""select sum(actual_qty) from tabBin
		where item_code=%s {condition}""",
		values,
	)[0][0]

	return actual_qty


def get_latest_stock_balance():
	bin_map = {}
	for d in frappe.db.sql(
		"""SELECT item_code, warehouse, stock_value as stock_value
		FROM tabBin""",
		as_dict=1,
	):
		bin_map.setdefault(d.warehouse, {}).setdefault(d.item_code, flt(d.stock_value))

	return bin_map


def get_bin(item_code, warehouse):
	bin = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
	if not bin:
		bin_obj = _create_bin(item_code, warehouse)
	else:
		bin_obj = frappe.get_doc("Bin", bin, for_update=True)
	bin_obj.flags.ignore_permissions = True
	return bin_obj


def get_or_make_bin(item_code: str, warehouse: str) -> str:
	bin_record = frappe.get_cached_value("Bin", {"item_code": item_code, "warehouse": warehouse})

	if not bin_record:
		bin_obj = _create_bin(item_code, warehouse)
		bin_record = bin_obj.name
	return bin_record


def _create_bin(item_code, warehouse):
	"""Create a bin and take care of concurrent inserts."""

	bin_creation_savepoint = "create_bin"
	try:
		frappe.db.savepoint(bin_creation_savepoint)
		bin_obj = frappe.get_doc(doctype="Bin", item_code=item_code, warehouse=warehouse)
		bin_obj.flags.ignore_permissions = 1
		bin_obj.insert()
	except frappe.UniqueValidationError:
		frappe.db.rollback(save_point=bin_creation_savepoint)  # preserve transaction in postgres
		bin_obj = frappe.get_last_doc("Bin", {"item_code": item_code, "warehouse": warehouse})

	return bin_obj


@frappe.whitelist()
def get_incoming_rate(args, raise_error_if_no_rate=True):
	"""Get Incoming Rate based on valuation method"""
	from erpnext.stock.stock_ledger import get_previous_sle, get_valuation_rate

	if isinstance(args, str):
		args = json.loads(args)

	in_rate = None

	item_details = frappe.get_cached_value(
		"Item", args.get("item_code"), ["has_serial_no", "has_batch_no"], as_dict=1
	)

	use_moving_avg_for_batch = frappe.db.get_single_value("Stock Settings", "do_not_use_batchwise_valuation")

	if isinstance(args, dict):
		args = frappe._dict(args)

	if item_details and item_details.has_serial_no and args.get("serial_and_batch_bundle"):
		args.actual_qty = args.qty
		sn_obj = SerialNoValuation(
			sle=args,
			warehouse=args.get("warehouse"),
			item_code=args.get("item_code"),
		)

		return sn_obj.get_incoming_rate()

	elif (
		item_details
		and item_details.has_batch_no
		and args.get("serial_and_batch_bundle")
		and not use_moving_avg_for_batch
	):
		args.actual_qty = args.qty
		batch_obj = BatchNoValuation(
			sle=args,
			warehouse=args.get("warehouse"),
			item_code=args.get("item_code"),
		)

		return batch_obj.get_incoming_rate()

	elif (args.get("serial_no") or "").strip() and not args.get("serial_and_batch_bundle"):
		args.actual_qty = args.qty
		args.serial_nos = get_serial_nos_data(args.get("serial_no"))

		sn_obj = SerialNoValuation(sle=args, warehouse=args.get("warehouse"), item_code=args.get("item_code"))

		return sn_obj.get_incoming_rate()
	elif args.get("batch_no") and not args.get("serial_and_batch_bundle") and not use_moving_avg_for_batch:
		args.actual_qty = args.qty
		args.batch_nos = frappe._dict({args.batch_no: args})

		batch_obj = BatchNoValuation(
			sle=args,
			warehouse=args.get("warehouse"),
			item_code=args.get("item_code"),
		)

		return batch_obj.get_incoming_rate()
	else:
		valuation_method = get_valuation_method(args.get("item_code"))
		previous_sle = get_previous_sle(args)
		if valuation_method in ("FIFO", "LIFO"):
			if previous_sle:
				previous_stock_queue = json.loads(previous_sle.get("stock_queue", "[]") or "[]")
				in_rate = (
					_get_fifo_lifo_rate(previous_stock_queue, args.get("qty") or 0, valuation_method)
					if previous_stock_queue
					else None
				)
		elif valuation_method == "Moving Average":
			in_rate = previous_sle.get("valuation_rate")

	if in_rate is None:
		voucher_no = args.get("voucher_no") or args.get("name")
		in_rate = get_valuation_rate(
			args.get("item_code"),
			args.get("warehouse"),
			args.get("voucher_type"),
			voucher_no,
			args.get("allow_zero_valuation"),
			currency=erpnext.get_company_currency(args.get("company")),
			company=args.get("company"),
			raise_error_if_no_rate=raise_error_if_no_rate,
		)

	return flt(in_rate)


def get_batch_incoming_rate(item_code, warehouse, batch_no, posting_date, posting_time, creation=None):
	sle = frappe.qb.DocType("Stock Ledger Entry")

	timestamp_condition = CombineDatetime(sle.posting_date, sle.posting_time) < CombineDatetime(
		posting_date, posting_time
	)
	if creation:
		timestamp_condition |= (
			CombineDatetime(sle.posting_date, sle.posting_time) == CombineDatetime(posting_date, posting_time)
		) & (sle.creation < creation)

	batch_details = (
		frappe.qb.from_(sle)
		.select(Sum(sle.stock_value_difference).as_("batch_value"), Sum(sle.actual_qty).as_("batch_qty"))
		.where(
			(sle.item_code == item_code)
			& (sle.warehouse == warehouse)
			& (sle.batch_no == batch_no)
			& (sle.serial_and_batch_bundle.isnull())
			& (sle.is_cancelled == 0)
		)
		.where(timestamp_condition)
	).run(as_dict=True)

	if batch_details and batch_details[0].batch_qty:
		return batch_details[0].batch_value / batch_details[0].batch_qty


def get_avg_purchase_rate(serial_nos):
	"""get average value of serial numbers"""

	serial_nos = get_valid_serial_nos(serial_nos)
	return flt(
		frappe.db.sql(
			"""select avg(purchase_rate) from `tabSerial No`
		where name in (%s)"""
			% ", ".join(["%s"] * len(serial_nos)),
			tuple(serial_nos),
		)[0][0]
	)


def get_valuation_method(item_code):
	"""get valuation method from item or default"""
	val_method = frappe.db.get_value("Item", item_code, "valuation_method", cache=True)
	if not val_method:
		val_method = frappe.db.get_value("Stock Settings", None, "valuation_method", cache=True) or "FIFO"
	return val_method


def get_fifo_rate(previous_stock_queue, qty):
	"""get FIFO (average) Rate from Queue"""
	return _get_fifo_lifo_rate(previous_stock_queue, qty, "FIFO")


def get_lifo_rate(previous_stock_queue, qty):
	"""get LIFO (average) Rate from Queue"""
	return _get_fifo_lifo_rate(previous_stock_queue, qty, "LIFO")


def _get_fifo_lifo_rate(previous_stock_queue, qty, method):
	ValuationKlass = LIFOValuation if method == "LIFO" else FIFOValuation

	stock_queue = ValuationKlass(previous_stock_queue)
	if flt(qty) >= 0:
		total_qty, total_value = stock_queue.get_total_stock_and_value()
		return total_value / total_qty if total_qty else 0.0
	else:
		popped_bins = stock_queue.remove_stock(abs(flt(qty)))

		total_qty, total_value = ValuationKlass(popped_bins).get_total_stock_and_value()
		return total_value / total_qty if total_qty else 0.0


def get_valid_serial_nos(sr_nos, qty=0, item_code=""):
	"""split serial nos, validate and return list of valid serial nos"""
	# TODO: remove duplicates in client side
	serial_nos = cstr(sr_nos).strip().replace(",", "\n").split("\n")

	valid_serial_nos = []
	for val in serial_nos:
		if val:
			val = val.strip()
			if val in valid_serial_nos:
				frappe.throw(_("Serial number {0} entered more than once").format(val))
			else:
				valid_serial_nos.append(val)

	if qty and len(valid_serial_nos) != abs(qty):
		frappe.throw(_("{0} valid serial nos for Item {1}").format(abs(qty), item_code))

	return valid_serial_nos


def validate_warehouse_company(warehouse, company):
	warehouse_company = frappe.db.get_value("Warehouse", warehouse, "company", cache=True)
	if warehouse_company and warehouse_company != company:
		frappe.throw(
			_("Warehouse {0} does not belong to company {1}").format(warehouse, company),
			InvalidWarehouseCompany,
		)


def is_group_warehouse(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "is_group", cache=True):
		frappe.throw(_("Group node warehouse is not allowed to select for transactions"))


def validate_disabled_warehouse(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "disabled", cache=True):
		frappe.throw(
			_("Disabled Warehouse {0} cannot be used for this transaction.").format(
				get_link_to_form("Warehouse", warehouse)
			)
		)


def update_included_uom_in_report(columns, result, include_uom, conversion_factors):
	if not include_uom or not conversion_factors:
		return

	is_dict_obj = False
	if isinstance(result[0], dict):
		is_dict_obj = True

	convertible_columns = {}
	for idx, d in enumerate(columns):
		key = d.get("fieldname") if is_dict_obj else idx
		if d.get("convertible"):
			convertible_columns.setdefault(key, d.get("convertible"))

			# Add new column to show qty/rate as per the selected UOM
			columns.insert(
				idx + 1,
				{
					"label": "{} (per {})".format(d.get("label"), include_uom),
					"fieldname": "{}_{}".format(d.get("fieldname"), frappe.scrub(include_uom)),
					"fieldtype": "Currency" if d.get("convertible") == "rate" else "Float",
				},
			)

	update_dict_values = []
	for row_idx, row in enumerate(result):
		data = row.items() if is_dict_obj else enumerate(row)
		for key, value in data:
			if key not in convertible_columns:
				continue
			# If no conversion factor for the UOM, defaults to 1
			if not conversion_factors[row_idx]:
				conversion_factors[row_idx] = 1

			if convertible_columns.get(key) == "rate":
				new_value = flt(value) * conversion_factors[row_idx]
			else:
				new_value = flt(value) / conversion_factors[row_idx]

			if not is_dict_obj:
				row.insert(key + 1, new_value)
			else:
				new_key = f"{key}_{frappe.scrub(include_uom)}"
				update_dict_values.append([row, new_key, new_value])

	for data in update_dict_values:
		row, key, value = data
		row[key] = value


def add_additional_uom_columns(columns, result, include_uom, conversion_factors):
	if not include_uom or not conversion_factors:
		return

	convertible_column_map = {}
	for col_idx in list(reversed(range(0, len(columns)))):
		col = columns[col_idx]
		if isinstance(col, dict) and col.get("convertible") in ["rate", "qty"]:
			next_col = col_idx + 1
			columns.insert(next_col, col.copy())
			columns[next_col]["fieldname"] += "_alt"
			convertible_column_map[col.get("fieldname")] = frappe._dict(
				{"converted_col": columns[next_col]["fieldname"], "for_type": col.get("convertible")}
			)
			if col.get("convertible") == "rate":
				columns[next_col]["label"] += f" (per {include_uom})"
			else:
				columns[next_col]["label"] += f" ({include_uom})"

	for row_idx, row in enumerate(result):
		for convertible_col, data in convertible_column_map.items():
			conversion_factor = conversion_factors.get(row.get("item_code")) or 1.0
			for_type = data.for_type
			value_before_conversion = row.get(convertible_col)
			if for_type == "rate":
				row[data.converted_col] = flt(value_before_conversion) * conversion_factor
			else:
				row[data.converted_col] = flt(value_before_conversion) / conversion_factor

		result[row_idx] = row


def get_incoming_outgoing_rate_for_cancel(item_code, voucher_type, voucher_no, voucher_detail_no):
	outgoing_rate = frappe.db.sql(
		"""SELECT CASE WHEN actual_qty = 0 THEN 0 ELSE abs(stock_value_difference / actual_qty) END
		FROM `tabStock Ledger Entry`
		WHERE voucher_type = %s and voucher_no = %s
			and item_code = %s and voucher_detail_no = %s
			ORDER BY CREATION DESC limit 1""",
		(voucher_type, voucher_no, item_code, voucher_detail_no),
	)

	outgoing_rate = outgoing_rate[0][0] if outgoing_rate else 0.0

	return outgoing_rate


def is_reposting_item_valuation_in_progress():
	reposting_in_progress = frappe.db.exists(
		"Repost Item Valuation", {"docstatus": 1, "status": ["in", ["Queued", "In Progress"]]}
	)
	if reposting_in_progress:
		frappe.msgprint(
			_("Item valuation reposting in progress. Report might show incorrect item valuation."), alert=1
		)


def check_pending_reposting(posting_date: str, throw_error: bool = True) -> bool:
	"""Check if there are pending reposting job till the specified posting date."""

	filters = {
		"docstatus": 1,
		"status": ["in", ["Queued", "In Progress"]],
		"posting_date": ["<=", posting_date],
	}

	reposting_pending = frappe.db.exists("Repost Item Valuation", filters)
	if reposting_pending and throw_error:
		msg = _(
			"Stock/Accounts can not be frozen as processing of backdated entries is going on. Please try again later."
		)
		frappe.msgprint(
			msg,
			raise_exception=PendingRepostingError,
			title="Stock Reposting Ongoing",
			indicator="red",
			primary_action={
				"label": _("Show pending entries"),
				"client_action": "erpnext.route_to_pending_reposts",
				"args": filters,
			},
		)

	return bool(reposting_pending)


@frappe.whitelist()
def scan_barcode(search_value: str) -> BarcodeScanResult:
	def set_cache(data: BarcodeScanResult):
		frappe.cache().set_value(f"erpnext:barcode_scan:{search_value}", data, expires_in_sec=120)

	def get_cache() -> BarcodeScanResult | None:
		if data := frappe.cache().get_value(f"erpnext:barcode_scan:{search_value}"):
			return data

	if scan_data := get_cache():
		return scan_data

	# search barcode no
	barcode_data = frappe.db.get_value(
		"Item Barcode",
		{"barcode": search_value},
		["barcode", "parent as item_code", "uom"],
		as_dict=True,
	)
	if barcode_data:
		_update_item_info(barcode_data)
		set_cache(barcode_data)
		return barcode_data

	# search serial no
	serial_no_data = frappe.db.get_value(
		"Serial No",
		search_value,
		["name as serial_no", "item_code", "batch_no"],
		as_dict=True,
	)
	if serial_no_data:
		_update_item_info(serial_no_data)
		set_cache(serial_no_data)
		return serial_no_data

	# search batch no
	batch_no_data = frappe.db.get_value(
		"Batch",
		search_value,
		["name as batch_no", "item as item_code"],
		as_dict=True,
	)
	if batch_no_data:
		if frappe.get_cached_value("Item", batch_no_data.item_code, "has_serial_no"):
			frappe.throw(
				_(
					"Batch No {0} is linked with Item {1} which has serial no. Please scan serial no instead."
				).format(search_value, batch_no_data.item_code)
			)

		_update_item_info(batch_no_data)
		set_cache(batch_no_data)
		return batch_no_data

	return {}


def _update_item_info(scan_result: dict[str, str | None]) -> dict[str, str | None]:
	if item_code := scan_result.get("item_code"):
		if item_info := frappe.get_cached_value(
			"Item",
			item_code,
			["has_batch_no", "has_serial_no"],
			as_dict=True,
		):
			scan_result.update(item_info)
	return scan_result


def get_combine_datetime(posting_date, posting_time):
	import datetime

	if isinstance(posting_date, str):
		posting_date = getdate(posting_date)

	if isinstance(posting_time, str):
		posting_time = get_time(posting_time)

	if isinstance(posting_time, datetime.timedelta):
		posting_time = (datetime.datetime.min + posting_time).time()

	return datetime.datetime.combine(posting_date, posting_time).replace(microsecond=0)
