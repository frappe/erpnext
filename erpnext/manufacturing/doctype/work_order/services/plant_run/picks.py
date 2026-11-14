import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	get_auto_batch_nos,
	get_available_serial_nos,
)
from erpnext.stock.serial_batch_bundle import SerialBatchCreation
from erpnext.stock.utils import get_combine_datetime


def get_pick_options(item_code, warehouse):
	item = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True)
	kwargs = frappe._dict(
		item_code=item_code,
		warehouse=warehouse,
		has_batch_no=item.has_batch_no,
		posting_datetime=now_datetime(),
	)
	if item.has_serial_no:
		serial_nos = get_available_serial_nos(kwargs)
		return {
			"serial_nos": [
				{"serial_no": row.serial_no, "batch_no": row.get("batch_no")} for row in serial_nos
			]
		}
	if not item.has_batch_no:
		return {}

	batches = [row for row in get_auto_batch_nos(kwargs) if flt(row.qty) > 0]
	details = get_batch_details([row.batch_no for row in batches])
	return {
		"batches": [
			{"batch_no": row.batch_no, "qty": flt(row.qty), **details.get(row.batch_no, {})}
			for row in batches
		]
	}


def get_batch_details(batch_nos):
	if not batch_nos:
		return {}
	batch = frappe.qb.DocType("Batch")
	rows = (
		frappe.qb.from_(batch)
		.select(batch.name, batch.batch_id, batch.expiry_date)
		.where(batch.name.isin(batch_nos))
		.run(as_dict=True)
	)
	return {row.name: {"batch_id": row.batch_id, "expiry_date": row.expiry_date} for row in rows}


class PickedSerialBatch:
	def __init__(self, entry, picks):
		self.entry = entry
		self.picks = picks or {}

	def apply(self):
		rows = {row.job_card_item: row for row in self.entry.items}
		for name, pick in self.picks.items():
			row = rows.get(name)
			if not row:
				frappe.throw(_("Serial and batch nos were picked for a material this stage does not consume"))
			self.set_bundle(row, pick)

	def set_bundle(self, row, pick):
		if row.serial_and_batch_bundle:
			frappe.throw(
				_("{0} already takes its serial and batch nos from the stage before").format(row.item_code)
			)

		serial_nos = list(pick.get("serial_nos") or [])
		batches = {
			batch_no: flt(qty) for batch_no, qty in (pick.get("batches") or {}).items() if flt(qty) > 0
		}
		qty = flt(row.qty) * flt(row.conversion_factor or 1)
		self.validate_qty(row, len(serial_nos) if serial_nos else sum(batches.values()), qty)

		bundle = SerialBatchCreation(
			{
				"item_code": row.item_code,
				"warehouse": row.s_warehouse,
				"posting_datetime": get_combine_datetime(self.entry.posting_date, self.entry.posting_time),
				"voucher_type": "Stock Entry",
				"company": self.entry.company,
				"type_of_transaction": "Outward",
				"qty": qty,
				"serial_nos": serial_nos,
				"batches": frappe._dict(batches) if not serial_nos else None,
				"do_not_submit": True,
			}
		).make_serial_and_batch_bundle()
		row.serial_and_batch_bundle = bundle.name
		row.use_serial_batch_fields = 0

	@staticmethod
	def validate_qty(row, picked, qty):
		precision = cint(frappe.get_precision("Stock Entry Detail", "transfer_qty")) or 3
		if flt(picked, precision) != flt(qty, precision):
			frappe.throw(
				_("Pick {0} of {1}. The picked serial and batch nos add up to {2}.").format(
					frappe.format(qty, "Float"), row.item_code, frappe.format(picked, "Float")
				)
			)
