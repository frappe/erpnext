from collections import Counter, defaultdict

import frappe
import frappe.query_builder
from frappe.query_builder.functions import Coalesce, Concat_ws
from frappe.utils import cint, today

from erpnext.stock.serial_batch_bundle.availability.reservations import (
	get_other_doc_reserved_serials,
	get_reserved_serial_nos_for_pos,
	get_reserved_serial_nos_for_sre,
	get_reserved_serial_nos_for_voucher,
	get_reserved_voucher_details,
)
from erpnext.stock.serial_batch_bundle.bundle_entries import parse_serial_nos


def get_available_serial_nos(kwargs):
	from erpnext.stock.utils import get_combine_datetime

	fields = ["name as serial_no", "warehouse"]
	if kwargs.has_batch_no:
		fields.append("batch_no")

	order_by = "creation"
	if kwargs.based_on == "LIFO":
		order_by = "creation"
	elif kwargs.based_on == "Expiry":
		order_by = "amc_expiry_date"

	if not kwargs.get("posting_datetime") and kwargs.get("posting_date"):
		kwargs["posting_datetime"] = get_combine_datetime(
			kwargs.get("posting_date"), kwargs.get("posting_time")
		)

	filters = {"item_code": kwargs.item_code}

	# ignore_warehouse is used for backdated stock transactions
	# There might be chances that the serial no not exists in the warehouse during backdated stock transactions
	if not kwargs.get("ignore_warehouse"):
		filters["warehouse"] = ("is", "set")
		if isinstance(kwargs.warehouse, list):
			filters["warehouse"] = ("in", kwargs.warehouse)
		elif kwargs.warehouse:
			filters["warehouse"] = kwargs.warehouse

	reserved_entries = [] if kwargs.get("ignore_reserved_stock") else get_reserved_serial_nos_for_sre(kwargs)

	ignore_serial_nos = []
	if reserved_entries:
		if kwargs.get("sabb_voucher_type") in ("Delivery Note", "Sales Invoice") and kwargs.get(
			"sales_order_item"
		):
			reserved_voucher_details = [kwargs.get("sales_order_item")]
		else:
			reserved_voucher_details = get_reserved_voucher_details(kwargs)

		# Check if serial nos are reserved for the current voucher then fetch those serial nos first
		if reserved_serial_nos := get_reserved_serial_nos_for_voucher(
			kwargs, reserved_entries, reserved_voucher_details
		):
			picked = get_reserved_serial_nos_in_stock(filters, fields, order_by, kwargs, reserved_serial_nos)
			pending_qty = cint(kwargs.qty) - len(picked)
			if pending_qty <= 0:
				return picked

			# the rest of the qty comes from unreserved stock
			skip_serial_nos = [*(kwargs.get("ignore_serial_nos") or []), *reserved_serial_nos]
			return picked + get_available_serial_nos(
				frappe._dict(
					kwargs, qty=pending_qty, ignore_serial_nos=skip_serial_nos, pick_reserved_items=False
				)
			)

		# Check if serial nos are reserved for other vouchers then ignore those serial nos
		elif ignore_reserved_serial_nos := get_other_doc_reserved_serials(
			kwargs, reserved_entries, reserved_voucher_details
		):
			ignore_serial_nos.extend(ignore_reserved_serial_nos)

	if reserved_for_pos := get_reserved_serial_nos_for_pos(kwargs):
		ignore_serial_nos.extend(reserved_for_pos)

	# To ignore serial nos in the same record for the draft state
	if kwargs.get("ignore_serial_nos"):
		ignore_serial_nos.extend(kwargs.get("ignore_serial_nos"))

	ignore_serial_nos = list(set(ignore_serial_nos))
	if kwargs.get("posting_datetime"):
		time_based_serial_nos = get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos)

		if not time_based_serial_nos:
			return []

		for sn in ignore_serial_nos:
			if sn in time_based_serial_nos:
				time_based_serial_nos.remove(sn)

		filters["name"] = ("in", time_based_serial_nos)
	elif kwargs.get("check_serial_nos") and kwargs.get("serial_nos"):
		ignore = set(ignore_serial_nos)
		serial_nos = [sn for sn in kwargs.get("serial_nos") if sn not in ignore]
		if not serial_nos:
			return []

		filters["name"] = ("in", serial_nos)
	elif ignore_serial_nos:
		filters["name"] = ("not in", ignore_serial_nos)
	elif kwargs.get("serial_nos"):
		filters["name"] = ("in", kwargs.get("serial_nos"))

	if not set_batch_filter(filters, kwargs):
		return []

	return get_serial_nos_based_on_filters(filters, fields, order_by, kwargs)


def get_reserved_serial_nos_in_stock(filters, fields, order_by, kwargs, reserved_serial_nos) -> list:
	"""Reserved serial nos available in the asked warehouse and batches."""
	ignore = set(kwargs.get("ignore_serial_nos") or [])
	reserved_serial_nos = [sn for sn in reserved_serial_nos if sn not in ignore]
	if not reserved_serial_nos or not set_batch_filter(filters, kwargs):
		return []

	return get_serial_nos_based_on_filters(
		{**filters, "name": ("in", reserved_serial_nos)}, fields, order_by, kwargs
	)


def set_batch_filter(filters, kwargs):
	if not kwargs.get("batches"):
		return True

	batches = get_non_expired_batches(kwargs.get("batches"))
	if not batches:
		return False

	filters["batch_no"] = ("in", batches)
	return True


def get_batch_expiry_date_column(serial_no):
	batch = frappe.qb.DocType("Batch")
	return frappe.qb.from_(batch).select(batch.expiry_date).where(batch.name == serial_no.batch_no)


def get_serial_nos_based_on_filters(filters, fields, order_by, kwargs):
	doctype = frappe.qb.DocType("Serial No")

	order_by_column = getattr(doctype, order_by)
	query = frappe.qb.from_(doctype).limit(cint(kwargs.qty) or 10000000).for_update()

	if kwargs.based_on == "LIFO":
		query = query.orderby(order_by_column, order=frappe.query_builder.Order.desc)
	elif kwargs.based_on == "Expiry":
		expiry_date = Coalesce(get_batch_expiry_date_column(doctype), doctype.amc_expiry_date, "9999-12-31")
		query = query.orderby(expiry_date).orderby(doctype.creation)
	else:
		query = query.orderby(order_by_column)

	for key, value in filters.items():
		column = getattr(doctype, key)

		if isinstance(value, tuple):
			operator = value[0]

			if operator == "between":
				query = query.where(column.between(value[1], value[2]))

			elif operator == "in":
				query = query.where(column.isin(value[1]))

			elif operator == "not in":
				query = query.where(column.notin(value[1]))

			elif operator == "is":
				if value[1] == "set":
					query = query.where(column.isnotnull())
				elif value[1] == "not set":
					query = query.where(column.isnull())
		else:
			query = query.where(column == value)

	for field in fields:
		if " as " in field.lower():
			# Split field and alias
			field_name, alias = field.split(" as ", 1)
			query = query.select(getattr(doctype, field_name).as_(alias))
		else:
			query = query.select(getattr(doctype, field))

	return query.run(as_dict=True)


def get_non_expired_batches(batches):
	filters = {}
	if isinstance(batches, list):
		filters["name"] = ("in", batches)
	else:
		filters["name"] = batches

	data = frappe.get_all(
		"Batch",
		filters=filters,
		or_filters=[["expiry_date", ">=", today()], ["expiry_date", "is", "not set"]],
		fields=["name"],
	)

	return [d.name for d in data] if data else []


def get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos):
	serial_nos = Counter()
	data = get_stock_ledgers_for_serial_nos(kwargs)

	bundle_wise_serial_nos = get_bundle_wise_serial_nos(data, kwargs)
	for d in data:
		if d.serial_and_batch_bundle:
			sns = bundle_wise_serial_nos.get(d.serial_and_batch_bundle, [])
		elif d.serial_no:
			sns = parse_serial_nos(d.serial_no)
		else:
			continue

		if d.actual_qty > 0:
			serial_nos.update(sns)
		else:
			# Keep outward balances when the inward entry has a later posting time.
			serial_nos.subtract(sns)

	ignore_serial_nos = set(ignore_serial_nos)
	return [
		serial_no for serial_no, qty in serial_nos.items() if qty > 0 and serial_no not in ignore_serial_nos
	]


def get_bundle_wise_serial_nos(data, kwargs):
	bundle_wise_serial_nos = defaultdict(list)
	bundles = list({d.serial_and_batch_bundle for d in data if d.serial_and_batch_bundle})
	if not bundles:
		return bundle_wise_serial_nos

	sabe = frappe.qb.DocType("Serial and Batch Entry")
	query = (
		frappe.qb.from_(sabe)
		.select(sabe.serial_no, sabe.parent)
		.where(sabe.parent.isin(bundles))
		.where(sabe.docstatus == 1)
		.where(sabe.serial_no.isnotnull())
		.where(sabe.serial_no != "")
	)

	if kwargs.get("check_serial_nos") and kwargs.get("serial_nos"):
		query = query.where(sabe.serial_no.isin(kwargs.get("serial_nos")))

	for d in query.run(as_dict=True):
		if d.parent:
			bundle_wise_serial_nos[d.parent].append(d.serial_no)

	return bundle_wise_serial_nos


def get_stock_ledgers_for_serial_nos(kwargs):
	"""
	Fetch stock ledger entries based on various filters.
	:param kwargs: Filters including posting_datetime, creation, warehouse, item_code, serial_nos, ignore_voucher_detail_no, voucher_no. Joins with Serial and Batch Entry table to filter based on serial numbers.
	:return: List of stock ledger entries as dictionaries.
	:rtype: list[dict]
	"""

	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	serial_batch_entry = frappe.qb.DocType("Serial and Batch Entry")

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.select(
			stock_ledger_entry.posting_datetime,
			stock_ledger_entry.actual_qty,
			stock_ledger_entry.serial_no,
			stock_ledger_entry.serial_and_batch_bundle,
			# creation is the ORDER BY tiebreaker; postgres requires ORDER BY columns to be in the
			# select list when the query is DISTINCT (added below for serial-no filters). It is unique
			# per SLE so it doesn't change the distinct row set (serial_and_batch_bundle already is).
			stock_ledger_entry.creation,
		)
		.where(stock_ledger_entry.is_cancelled == 0)
		.orderby(stock_ledger_entry.posting_datetime)
		.orderby(stock_ledger_entry.creation)
	)

	if kwargs.get("posting_datetime"):
		timestamp_condition = stock_ledger_entry.posting_datetime <= kwargs.posting_datetime

		if kwargs.get("creation"):
			timestamp_condition = stock_ledger_entry.posting_datetime < kwargs.posting_datetime

			timestamp_condition |= (stock_ledger_entry.posting_datetime == kwargs.posting_datetime) & (
				stock_ledger_entry.creation < kwargs.creation
			)

		query = query.where(timestamp_condition)

	for field in ["warehouse", "item_code"]:
		if not kwargs.get(field):
			continue

		if isinstance(kwargs.get(field), list):
			query = query.where(stock_ledger_entry[field].isin(kwargs.get(field)))
		else:
			query = query.where(stock_ledger_entry[field] == kwargs.get(field))

	serial_nos = kwargs.get("serial_nos") or kwargs.get("serial_no")
	if serial_nos and not isinstance(serial_nos, list):
		serial_nos = [serial_nos]

	if serial_nos:
		import re

		escaped_serial_nos = [re.escape(sn) for sn in serial_nos if sn]
		regex_pattern = r"\n(" + "|".join(escaped_serial_nos) + r")\n"

		query = (
			query.left_join(serial_batch_entry)
			.on(stock_ledger_entry.serial_and_batch_bundle == serial_batch_entry.parent)
			.where(
				serial_batch_entry.serial_no.isin(serial_nos)
				| Concat_ws("", "\n", stock_ledger_entry.serial_no, "\n").regexp(regex_pattern)
			)
			.distinct()
		)

	if kwargs.ignore_voucher_detail_no:
		query = query.where(stock_ledger_entry.voucher_detail_no != kwargs.ignore_voucher_detail_no)

	elif kwargs.voucher_no:
		query = query.where(stock_ledger_entry.voucher_no != kwargs.voucher_no)

	return query.run(as_dict=True)
