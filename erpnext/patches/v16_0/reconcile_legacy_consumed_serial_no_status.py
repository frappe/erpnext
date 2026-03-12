from collections import defaultdict

import frappe
from frappe.query_builder.functions import IfNull
from frappe.utils import flt, get_datetime

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as parse_serial_nos

CONSUMED_STOCK_ENTRY_PURPOSES = {
	"Manufacture",
	"Material Issue",
	"Repack",
	"Material Consumption for Manufacture",
}

BUNDLE_QUERY_CHUNK_SIZE = 500


def execute():
	"""Reconcile legacy raw-material serials left as Delivered instead of Consumed.

	This backfills serials affected by older ERPNext behavior where outward raw
	material movements in manufacturing-related stock entries could leave the
	serial status as Delivered. The patch starts from a narrow Delivered seed set,
	rebuilds each serial's effective history from both Serial and Batch Bundles
	and legacy Stock Ledger Entry serial fields, and only updates rows whose
	latest non-cancelled movement is an outward Stock Entry for a purpose that
	now maps to Consumed.
	"""
	updates = get_consumed_serial_no_status_updates()
	if not updates:
		print("No legacy serial nos required status reconciliation.")
		return

	updated_serial_nos = [update["serial_no"] for update in updates]
	original_auto_commit = frappe.db.auto_commit_on_many_writes
	if len(updates) > 20000:
		frappe.db.auto_commit_on_many_writes = True

	try:
		for update in updates:
			frappe.db.set_value(
				"Serial No",
				update["serial_no"],
				{
					"status": "Consumed",
					# Clear stale warranty values that were set while the serial was
					# incorrectly treated as Delivered.
					"warranty_expiry_date": None,
					"warranty_period": 0,
				},
				update_modified=False,
			)
	finally:
		frappe.db.auto_commit_on_many_writes = original_auto_commit

	print(f"Updated {len(updated_serial_nos)} legacy serial nos from Delivered to Consumed.")
	print("Updated serial nos: " + ", ".join(updated_serial_nos))


def get_consumed_serial_no_status_updates(serial_no=None, limit=None):
	"""Return legacy Delivered serials whose latest effective movement should be Consumed."""
	if limit is not None:
		limit = int(limit)

	candidates = get_candidate_serial_nos(serial_no=serial_no)
	if not candidates:
		return []

	item_wise_serial_nos = defaultdict(set)
	for candidate in candidates:
		item_wise_serial_nos[candidate.item_code].add(candidate.name)

	history_by_serial = defaultdict(list)
	for movement in get_bundle_movements([candidate.name for candidate in candidates]):
		history_by_serial[movement.serial_no].append(movement)

	for item_code, serial_nos in item_wise_serial_nos.items():
		for movement in get_legacy_movements(item_code, serial_nos):
			history_by_serial[movement.serial_no].append(movement)

	updates = []
	for candidate in candidates:
		movements = sorted(history_by_serial.get(candidate.name, ()), key=_movement_sort_key)
		if not movements:
			continue

		latest_movement = movements[-1]
		if latest_movement.actual_qty >= 0 or latest_movement.voucher_type != "Stock Entry":
			continue

		purpose = frappe.get_cached_value("Stock Entry", latest_movement.voucher_no, "purpose")
		if purpose not in CONSUMED_STOCK_ENTRY_PURPOSES:
			continue

		updates.append(
			{
				"serial_no": candidate.name,
				"item_code": candidate.item_code,
				"current_status": "Delivered",
				"current_warranty_period": candidate.warranty_period,
				"current_warranty_expiry_date": candidate.warranty_expiry_date,
				"expected_status": "Consumed",
				"latest_voucher_type": latest_movement.voucher_type,
				"latest_voucher_no": latest_movement.voucher_no,
				"latest_stock_entry_purpose": purpose,
				"latest_posting_datetime": str(latest_movement.posting_datetime),
			}
		)

	updates.sort(key=lambda row: row["serial_no"])
	if limit is not None:
		return updates[:limit]

	return updates


def get_candidate_serial_nos(serial_no=None):
	filters = {
		"status": "Delivered",
		"warehouse": ("is", "not set"),
		"customer": ("is", "not set"),
	}
	if serial_no:
		filters["name"] = serial_no

	return frappe.get_all(
		"Serial No",
		fields=[
			"name",
			"item_code",
			"warranty_period",
			"warranty_expiry_date",
		],
		filters=filters,
		order_by="name asc",
	)


def get_bundle_movements(serial_nos):
	if not serial_nos:
		return []

	sbe = frappe.qb.DocType("Serial and Batch Entry")
	sabb = frappe.qb.DocType("Serial and Batch Bundle")

	movements = []
	for serial_chunk in _chunked(serial_nos, BUNDLE_QUERY_CHUNK_SIZE):
		rows = (
			frappe.qb.from_(sbe)
			.inner_join(sabb)
			.on(sabb.name == sbe.parent)
			.select(
				sbe.serial_no,
				sbe.qty.as_("actual_qty"),
				sabb.voucher_type,
				sabb.voucher_no,
				sabb.posting_date,
				sabb.posting_time,
				sabb.creation,
			)
			.where((sbe.serial_no.isin(serial_chunk)) & (sabb.docstatus == 1))
		).run(as_dict=True)

		for row in rows:
			movements.append(_make_movement(row, row.serial_no))

	return movements


def get_legacy_movements(item_code, candidate_serial_nos):
	if not candidate_serial_nos:
		return []

	sle = frappe.qb.DocType("Stock Ledger Entry")
	rows = (
		frappe.qb.from_(sle)
		.select(
			sle.voucher_type,
			sle.voucher_no,
			sle.posting_date,
			sle.posting_time,
			sle.creation,
			sle.actual_qty,
			sle.serial_no,
		)
		.where(
			(sle.item_code == item_code)
			& (sle.is_cancelled == 0)
			& (IfNull(sle.serial_no, "") != "")
			& (IfNull(sle.serial_and_batch_bundle, "") == "")
		)
		.orderby(sle.posting_datetime)
		.orderby(sle.creation)
	).run(as_dict=True)

	movements = []
	for row in rows:
		matched_serial_nos = set(parse_serial_nos(row.serial_no)).intersection(candidate_serial_nos)
		for serial_no in matched_serial_nos:
			movements.append(_make_movement(row, serial_no))

	return movements


def _make_movement(row, serial_no):
	posting_time = row.posting_time or "00:00:00"
	posting_datetime = get_datetime(f"{row.posting_date} {posting_time}")

	return frappe._dict(
		{
			"serial_no": serial_no,
			"voucher_type": row.voucher_type,
			"voucher_no": row.voucher_no,
			"posting_datetime": posting_datetime,
			"creation": get_datetime(row.creation) if row.creation else posting_datetime,
			"actual_qty": flt(row.actual_qty),
		}
	)


def _movement_sort_key(movement):
	return (
		movement.posting_datetime,
		movement.creation,
		movement.voucher_type,
		movement.voucher_no,
		movement.actual_qty,
	)


def _chunked(values, chunk_size):
	for index in range(0, len(values), chunk_size):
		yield values[index : index + chunk_size]
