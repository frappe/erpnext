# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import create_batch, flt, get_datetime
from pypika import functions as fn

ORIGINAL_PATCH = "erpnext.patches.v16_0.repair_work_order_material_transfer"
BATCH_SIZE = 1000
TERMINAL_STATUSES = ("Stopped", "Closed", "Completed")


def execute():
	patch_run_at = get_original_patch_run_at()
	if not patch_run_at:
		return

	updates = get_undo_updates(patch_run_at)
	if updates:
		frappe.db.bulk_update("Work Order", updates, update_modified=False)


def get_original_patch_run_at():
	return frappe.db.get_value("Patch Log", {"patch": ORIGINAL_PATCH, "skipped": 0}, "creation")


def get_undo_updates(patch_run_at=None):
	patch_run_at = patch_run_at or get_original_patch_run_at()
	if not patch_run_at:
		return {}
	patch_run_at = get_datetime(patch_run_at)

	work_orders = _get_candidate_work_orders(patch_run_at)
	for name in _get_work_orders_with_later_stock_entries(work_orders, patch_run_at):
		work_orders.pop(name, None)

	claimed_qty = _get_claimed_qty(work_orders)
	transferred_qty = _get_transferred_qty(work_orders)
	precision = frappe.get_precision("Work Order Item", "required_qty")
	updates = {}
	for name, values in work_orders.items():
		if not _has_full_coverage_at_precision(values, precision):
			continue
		if not _matches_cached_transfers(values, transferred_qty.get(name, {})):
			continue

		legacy_qty = _get_legacy_material_transferred(
			values, claimed_qty.get(name), transferred_qty.get(name, {})
		)
		if legacy_qty < values["current_qty"]:
			updates[name] = {"material_transferred_for_manufacturing": legacy_qty}

	return updates


def _get_candidate_work_orders(patch_run_at):
	work_orders = {}
	for row in _get_candidate_rows(patch_run_at):
		values = work_orders.setdefault(
			row.work_order,
			{
				"qty": flt(row.qty),
				"current_qty": flt(row.current_qty),
				"required_qty": {},
				"transferred_qty": {},
				"changed_after_patch": False,
			},
		)
		item_code = row.item_code
		values["required_qty"][item_code] = values["required_qty"].get(item_code, 0.0) + flt(row.required_qty)
		values["transferred_qty"][item_code] = max(
			values["transferred_qty"].get(item_code, 0.0), flt(row.transferred_qty)
		)
		values["changed_after_patch"] |= get_datetime(row.item_modified) > patch_run_at

	return {name: values for name, values in work_orders.items() if not values["changed_after_patch"]}


def _get_candidate_rows(patch_run_at):
	work_order = frappe.qb.DocType("Work Order")
	required_item = frappe.qb.DocType("Work Order Item")
	return (
		frappe.qb.from_(work_order)
		.inner_join(required_item)
		.on(required_item.parent == work_order.name)
		.select(
			work_order.name.as_("work_order"),
			work_order.qty,
			work_order.material_transferred_for_manufacturing.as_("current_qty"),
			required_item.item_code,
			required_item.required_qty,
			required_item.transferred_qty,
			required_item.modified.as_("item_modified"),
		)
		.where(
			(work_order.docstatus == 1)
			& (work_order.status.notin(TERMINAL_STATUSES))
			& (fn.Coalesce(work_order.skip_transfer, 0) == 0)
			& (fn.Coalesce(work_order.track_semi_finished_goods, 0) == 0)
			& (work_order.material_transferred_for_manufacturing == work_order.qty)
			& (fn.Coalesce(work_order.transfer_material_against, "") != "Job Card")
			& (work_order.creation <= patch_run_at)
			& (work_order.modified <= patch_run_at)
			& (required_item.include_item_in_manufacturing == 1)
			& (required_item.required_qty > 0)
		)
	).run(as_dict=True)


def _get_work_orders_with_later_stock_entries(work_orders, patch_run_at):
	changed_work_orders = set()
	stock_entry = frappe.qb.DocType("Stock Entry")
	for names in create_batch(list(work_orders), BATCH_SIZE):
		rows = (
			frappe.qb.from_(stock_entry)
			.select(stock_entry.work_order)
			.where(
				(stock_entry.work_order.isin(names))
				& ((stock_entry.creation > patch_run_at) | (stock_entry.modified > patch_run_at))
			)
			.groupby(stock_entry.work_order)
		).run(as_dict=True)
		changed_work_orders.update(row.work_order for row in rows)

	return changed_work_orders


def _get_claimed_qty(work_orders):
	claimed_qty = {}
	stock_entry = frappe.qb.DocType("Stock Entry")
	job_card = frappe.qb.DocType("Job Card")
	for names in create_batch(list(work_orders), BATCH_SIZE):
		rows = (
			frappe.qb.from_(stock_entry)
			.left_join(job_card)
			.on(stock_entry.job_card == job_card.name)
			.select(stock_entry.work_order, Sum(stock_entry.fg_completed_qty).as_("qty"))
			.where(
				(stock_entry.work_order.isin(names))
				& (stock_entry.docstatus == 1)
				& (stock_entry.purpose == "Material Transfer for Manufacture")
				& (stock_entry.is_additional_transfer_entry == 0)
				& (IfNull(job_card.is_corrective_job_card, 0) == 0)
			)
			.groupby(stock_entry.work_order)
		).run(as_dict=True)
		claimed_qty.update({row.work_order: flt(row.qty) for row in rows})

	return claimed_qty


def _get_transferred_qty(work_orders):
	transferred_qty = {}
	stock_entry = frappe.qb.DocType("Stock Entry")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
	job_card = frappe.qb.DocType("Job Card")
	for names in create_batch(list(work_orders), BATCH_SIZE):
		rows = (
			frappe.qb.from_(stock_entry)
			.inner_join(stock_entry_detail)
			.on(stock_entry_detail.parent == stock_entry.name)
			.left_join(job_card)
			.on(stock_entry.job_card == job_card.name)
			.select(
				stock_entry.work_order,
				stock_entry_detail.item_code,
				stock_entry_detail.original_item,
				Sum(stock_entry_detail.transfer_qty).as_("qty"),
			)
			.where(
				(stock_entry.work_order.isin(names))
				& (stock_entry.docstatus == 1)
				& (stock_entry.purpose == "Material Transfer for Manufacture")
				& (stock_entry.is_return == 0)
				& (IfNull(job_card.is_corrective_job_card, 0) == 0)
			)
			.groupby(stock_entry.work_order, stock_entry_detail.item_code, stock_entry_detail.original_item)
		).run(as_dict=True)

		for row in rows:
			item_code = row.original_item or row.item_code
			work_order_qty = transferred_qty.setdefault(row.work_order, {})
			work_order_qty[item_code] = work_order_qty.get(item_code, 0.0) + flt(row.qty)

	return transferred_qty


def _has_full_coverage_at_precision(values, precision):
	coverage = []
	for item_code, required_qty in values["required_qty"].items():
		transferred_qty = flt(values["transferred_qty"].get(item_code))
		if flt(transferred_qty, precision) == flt(required_qty, precision):
			coverage.append(1.0)
		else:
			coverage.append(transferred_qty / required_qty)

	return min(coverage, default=0.0) >= 1.0


def _matches_cached_transfers(values, transferred_qty):
	# The original patch stored no affected-row list. Matching the source ledger to its cache
	# avoids changing Work Orders whose transfer state became stale outside that patch.
	return all(
		flt(values["transferred_qty"].get(item_code)) == flt(transferred_qty.get(item_code))
		for item_code in values["required_qty"]
	)


def _get_legacy_material_transferred(values, claimed_qty, transferred_qty):
	if claimed_qty:
		return flt(claimed_qty)

	coverage = min(
		(
			flt(transferred_qty.get(item_code)) / required_qty
			for item_code, required_qty in values["required_qty"].items()
		),
		default=0.0,
	)
	return min(coverage, 1.0) * values["qty"]
