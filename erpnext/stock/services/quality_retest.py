# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Periodic re-test of stored batches.

Industries like pharmaceuticals re-inspect stored stock on an interval. A
"Periodic Re-test" quality trigger declares the interval; this scheduler watches
each batch's next_quality_inspection_date and, when it arrives, auto-transfers
the batch into the Quality Control warehouse. From there the standard quarantine
machinery applies: a Quality Control Lot is minted, the stock is locked, and a
Quality Inspection decision releases or rejects it. The inspection decision
schedules the next re-test.
"""

import frappe
from frappe.utils import add_days, flt, getdate, today
from frappe.utils.nestedset import get_descendants_of

from erpnext.stock.services.quality_trigger_resolution import _ordered_triggers
from erpnext.stock.services.quality_warehouse import (
	get_quality_warehouse,
	is_quality_warehouse,
	is_transit_warehouse,
)


def get_retest_trigger(item_code):
	"""The item's Periodic Re-test trigger, respecting Item / Item Group precedence."""
	for trigger in _ordered_triggers(item_code):
		if trigger.get("trigger_type") == "Periodic Re-test":
			return trigger
	return None


def items_with_retest_triggers():
	rows = frappe.get_all(
		"Item Quality Trigger",
		filters={"trigger_type": "Periodic Re-test"},
		fields=["parent", "parenttype"],
	)

	items = set()
	groups = set()
	for row in rows:
		if row.parenttype == "Item":
			items.add(row.parent)
		elif row.parenttype == "Item Group":
			groups.add(row.parent)
			groups.update(get_descendants_of("Item Group", row.parent))

	if groups:
		items.update(
			frappe.get_all(
				"Item",
				filters={"item_group": ("in", list(groups)), "has_batch_no": 1, "disabled": 0},
				pluck="name",
			)
		)

	return items


def process_periodic_retests():
	"""Daily: initialise re-test dates and quarantine batches that are due."""
	current_date = getdate(today())

	for item_code in items_with_retest_triggers():
		if not frappe.get_cached_value("Item", item_code, "has_batch_no"):
			continue

		trigger = get_retest_trigger(item_code)
		if not trigger or not trigger.retest_interval_days:
			continue

		batches = frappe.get_all(
			"Batch",
			filters={"item": item_code, "disabled": 0},
			fields=["name", "manufacturing_date", "next_quality_inspection_date", "creation"],
		)

		for batch in batches:
			if not batch.next_quality_inspection_date:
				base = batch.manufacturing_date or getdate(batch.creation)
				batch.next_quality_inspection_date = add_days(base, trigger.retest_interval_days)
				frappe.db.set_value(
					"Batch",
					batch.name,
					"next_quality_inspection_date",
					batch.next_quality_inspection_date,
					update_modified=False,
				)
				# no skip: a batch already past its computed date is due right now

			if getdate(batch.next_quality_inspection_date) <= current_date:
				quarantine_batch_for_retest(item_code, batch.name)


def quarantine_batch_for_retest(item_code, batch_no):
	"""Transfer a due batch into the Quality Control warehouse for re-inspection.

	The transfer mints the Quality Control Lot via the standard quarantine hook.
	The re-test date is cleared while the batch is under inspection — the
	inspection decision schedules the next one.
	"""
	from erpnext.stock.doctype.batch.batch import get_batch_qty

	transferred = False
	for held in get_batch_qty(batch_no=batch_no) or []:
		warehouse, qty = held.get("warehouse"), flt(held.get("qty"))
		if qty <= 0 or is_quality_warehouse(warehouse) or is_transit_warehouse(warehouse):
			continue

		quality_warehouse = get_quality_warehouse(warehouse)
		if not quality_warehouse:
			continue  # not configured for this store; retried on the next run

		from erpnext.stock.services.quality_quarantine import stamp_tracking_on_outward_row

		company = frappe.get_cached_value("Warehouse", warehouse, "company")
		transfer = frappe.new_doc("Stock Entry")
		transfer.purpose = "Material Transfer"
		transfer.stock_entry_type = "Material Transfer"
		transfer.company = company
		transfer_row = {
			"item_code": item_code,
			"qty": qty,
			"s_warehouse": warehouse,
			"t_warehouse": quality_warehouse,
		}
		stamp_tracking_on_outward_row(
			transfer_row,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			company=company,
			batch_no=batch_no,
		)
		transfer.append("items", transfer_row)
		transfer.flags.ignore_permissions = True
		transfer.insert()
		transfer.submit()
		transferred = True

	if transferred:
		frappe.db.set_value("Batch", batch_no, "next_quality_inspection_date", None, update_modified=False)

	return transferred


def schedule_next_retest(item_code, batch_no):
	"""Called when an inspection decision lands on a batch-carrying lot."""
	trigger = get_retest_trigger(item_code)
	if trigger and trigger.retest_interval_days:
		frappe.db.set_value(
			"Batch",
			batch_no,
			"next_quality_inspection_date",
			add_days(today(), trigger.retest_interval_days),
			update_modified=False,
		)
