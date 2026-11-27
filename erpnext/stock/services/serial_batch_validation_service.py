from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import escape_html, flt, get_link_to_form, getdate

from erpnext.stock.serial_batch_bundle.availability.batches import get_batch_qty_for_stock
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService


class SerialBatchValidationService:
	def __init__(self, doc) -> None:
		self.doc = doc

	def validate_duplicate_serial_and_batch_bundle(self, table_name):
		if not self.doc.get(table_name):
			return

		sbb_list = []
		for item in self.doc.get(table_name):
			if item.get("serial_and_batch_bundle"):
				sbb_list.append(item.get("serial_and_batch_bundle"))

			if item.get("rejected_serial_and_batch_bundle"):
				sbb_list.append(item.get("rejected_serial_and_batch_bundle"))

		if sbb_list:
			SLE = frappe.qb.DocType("Stock Ledger Entry")
			data = (
				frappe.qb.from_(SLE)
				.select(SLE.voucher_type, SLE.voucher_no, SLE.serial_and_batch_bundle)
				.where(
					(SLE.docstatus == 1)
					& (SLE.serial_and_batch_bundle.notnull())
					& (SLE.serial_and_batch_bundle.isin(sbb_list))
				)
				.limit(1)
			).run(as_dict=True)

			if data:
				data = data[0]
				frappe.throw(
					_("Serial and Batch Bundle {0} is already used in {1} {2}.").format(
						frappe.bold(data.serial_and_batch_bundle), data.voucher_type, data.voucher_no
					)
				)

	def validate_warehouse_of_sabb(self):
		is_internal_transfer = self.doc.is_internal_transfer()
		doc_before_save = self.doc.get_doc_before_save()
		bundle_details = {}

		for row in self.doc.items:
			for fieldname in ("serial_and_batch_bundle", "rejected_serial_and_batch_bundle"):
				bundle = row.get(fieldname)
				if not bundle:
					continue

				if bundle not in bundle_details:
					bundle_details[bundle] = frappe.db.get_value(
						"Serial and Batch Bundle",
						bundle,
						["company", "type_of_transaction", "warehouse", "has_serial_no"],
						as_dict=True,
					)

				sabb_details = bundle_details[bundle]
				if sabb_details and sabb_details.company != self.doc.company:
					frappe.throw(
						_(
							"Row #{0}: Company {1} does not match with the company {2} in Serial and Batch Bundle {3}."
						).format(row.idx, self.doc.company, sabb_details.company, bundle)
					)

			sabb_details = bundle_details.get(row.get("serial_and_batch_bundle"))
			if not sabb_details:
				continue

			if is_internal_transfer or sabb_details.type_of_transaction != "Outward":
				continue

			warehouse = row.get("warehouse") or row.get("s_warehouse")
			if sabb_details.warehouse != warehouse:
				frappe.throw(
					_(
						"Row #{0}: Warehouse {1} does not match with the warehouse {2} in Serial and Batch Bundle {3}."
					).format(row.idx, warehouse, sabb_details.warehouse, row.serial_and_batch_bundle)
				)

			if self.doc.doctype == "Stock Reconciliation":
				continue

			if sabb_details.has_serial_no and doc_before_save and doc_before_save.get("items"):
				prev_row = doc_before_save.get("items", {"idx": row.idx})
				if prev_row and prev_row[0].serial_and_batch_bundle != row.serial_and_batch_bundle:
					sabb_doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
					sabb_doc.validate_serial_no_status()

	def validate_serialized_batch(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		is_material_issue = False
		if self.doc.doctype == "Stock Entry" and self.doc.purpose in ["Material Issue", "Material Transfer"]:
			is_material_issue = True

		check_batches = self.is_batch_check_needed()
		# packed rows on batch fields get their bundle only at submit
		for d in self.doc.get("items") + SerialBatchBundleService(self.doc).get_current_packed_rows():
			if hasattr(d, "serial_no") and hasattr(d, "batch_no") and d.serial_no and d.batch_no:
				serial_nos = SerialBatchIdentity("Serial No").get_records(
					d.item_code, get_serial_nos(d.serial_no), ["batch_no", "serial_no", "warehouse"]
				)

				for row in serial_nos:
					if row.warehouse and row.batch_no != d.batch_no:
						frappe.throw(
							_("Row #{0}: Serial No {1} does not belong to Batch {2}").format(
								d.idx,
								escape_html(row.serial_no),
								SerialBatchIdentity("Batch").get_label(d.batch_no),
							)
						)

			if (
				check_batches
				and flt(d.qty) > 0.0
				and d.get("batch_no")
				and self.doc.get("posting_date")
				and self.doc.docstatus < 2
			):
				expiry_date, disabled = frappe.get_cached_value(
					"Batch", d.get("batch_no"), ["expiry_date", "disabled"]
				)
				self.validate_batch_is_usable(
					d.idx, d.batch_no, None if is_material_issue else expiry_date, disabled
				)

		if check_batches:
			self.validate_outward_bundle_batches(check_expiry=not is_material_issue)

	def is_batch_check_needed(self) -> bool:
		"""An invoice without Update Stock moves no stock, so its batches were checked when they moved.
		A consolidated invoice repeats POS Invoices whose batches were checked when sold."""
		if self.doc.flags.is_consolidated:
			return False

		is_invoice = self.doc.doctype in ("Sales Invoice", "Purchase Invoice")
		return not is_invoice or bool(self.doc.get("update_stock"))

	def validate_batch_is_usable(self, idx, batch_no, expiry_date, disabled):
		from erpnext.exceptions import BatchExpiredError

		if disabled:
			frappe.throw(
				_("Row #{0}: The batch {1} is disabled.").format(
					idx,
					get_link_to_form("Batch", batch_no, SerialBatchIdentity("Batch").get_label(batch_no)),
				)
			)

		if expiry_date and getdate(expiry_date) < getdate(self.doc.posting_date):
			frappe.throw(
				_("Row #{0}: The batch {1} has already expired.").format(
					idx,
					get_link_to_form("Batch", batch_no, SerialBatchIdentity("Batch").get_label(batch_no)),
				),
				BatchExpiredError,
			)

	def validate_outward_bundle_batches(self, check_expiry=True, rows=None, qty_field="qty"):
		if self.doc.get("is_return") or not self.doc.get("posting_date") or self.doc.docstatus == 2:
			return

		if rows is None:
			rows = (self.doc.get("items") or []) + (self.doc.get("packed_items") or [])

		row_idx_by_bundle = {
			d.serial_and_batch_bundle: d.idx
			for d in rows
			if d.get("serial_and_batch_bundle") and flt(d.get(qty_field)) > 0
		}
		if not row_idx_by_bundle:
			return

		posting_date = self.doc.posting_date if check_expiry else None
		for row in get_unusable_outward_bundle_batches(list(row_idx_by_bundle), posting_date):
			self.validate_batch_is_usable(
				row_idx_by_bundle[row.bundle],
				row.batch_no,
				row.expiry_date if check_expiry else None,
				row.disabled,
			)

	def validate_reserved_batches(self):
		if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
			return

		if self.doc.doctype not in ["Delivery Note", "Sales Invoice", "Stock Entry", "Stock Reconciliation"]:
			return

		batches = frappe.get_all(
			"Serial and Batch Entry",
			filters={
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"docstatus": 1,
				"batch_no": ("is", "set"),
				"qty": ("<", 0),
			},
			pluck="batch_no",
		)

		if not batches:
			return

		reference_fields = {
			"Sales Invoice": ["sales_order"],
			"Delivery Note": ["against_sales_order"],
			"Stock Entry": ["work_order", "subcontracting_inward_order"],
		}.get(self.doc.doctype, [])

		items = self.doc.items
		if self.doc.doctype == "Stock Entry":
			items = [self.doc]

		own_vouchers = {item.get(field) for item in items for field in reference_fields if item.get(field)}

		outstanding_qty = defaultdict(float)
		reservations = defaultdict(list)
		for row in self.get_reserved_batches(batches):
			if row.voucher_no in own_vouchers:
				continue

			key = (row.batch_no, row.warehouse)
			outstanding = flt(row.qty) - flt(row.delivered_qty)
			outstanding_qty[key] += outstanding
			if outstanding > 0:
				reservations[key].append(row)

		precision = frappe.get_precision("Serial and Batch Entry", "qty")
		for (batch_no, warehouse), reserved_qty in outstanding_qty.items():
			if flt(reserved_qty, precision) <= 0:
				continue

			batch_qty = get_batch_qty_for_stock(
				batch_no,
				warehouse,
				posting_date=self.doc.posting_date,
				posting_time=self.doc.posting_time,
				consider_negative_batches=True,
			)

			if flt(batch_qty, precision) >= flt(reserved_qty, precision):
				continue

			vouchers = ", ".join(
				f"{frappe.bold(voucher_type)} {frappe.bold(voucher_no)}"
				for voucher_type, voucher_no in dict.fromkeys(
					(row.voucher_type, row.voucher_no) for row in reservations[(batch_no, warehouse)]
				)
			)
			frappe.throw(
				_(
					"The batch {0} is reserved for {1} in the warehouse {2} and the remaining quantity is not enough to cover the reservations. So, cannot proceed with the {3} {4}."
				).format(
					frappe.bold(SerialBatchIdentity("Batch").get_label(batch_no)),
					vouchers,
					frappe.bold(warehouse),
					frappe.bold(self.doc.doctype),
					frappe.bold(self.doc.name),
				),
				title=_("Reserved Batch Conflict"),
			)

	def get_reserved_batches(self, batches):
		doctype = frappe.qb.DocType("Stock Reservation Entry")
		child_doc = frappe.qb.DocType("Serial and Batch Entry")

		return (
			frappe.qb.from_(doctype)
			.join(child_doc)
			.on(doctype.name == child_doc.parent)
			.select(
				child_doc.batch_no,
				child_doc.qty,
				child_doc.delivered_qty,
				doctype.voucher_type,
				doctype.voucher_no,
				doctype.warehouse,
			)
			.where((doctype.docstatus == 1) & (child_doc.batch_no.isin(batches)))
		).run(as_dict=True)


def get_unusable_outward_bundle_batches(bundles, posting_date):
	bundle = frappe.qb.DocType("Serial and Batch Bundle")
	entry = frappe.qb.DocType("Serial and Batch Entry")
	batch = frappe.qb.DocType("Batch")

	return (
		frappe.qb.from_(entry)
		.join(bundle)
		.on(entry.parent == bundle.name)
		.join(batch)
		.on(entry.batch_no == batch.name)
		.select(bundle.name.as_("bundle"), entry.batch_no, batch.expiry_date, batch.disabled)
		.where(
			bundle.name.isin(bundles)
			& (bundle.type_of_transaction == "Outward")
			& (unusable_batch_condition(batch, posting_date))
		)
		.run(as_dict=True)
	)


def unusable_batch_condition(batch, posting_date):
	if not posting_date:
		return batch.disabled == 1

	return (batch.expiry_date < getdate(posting_date)) | (batch.disabled == 1)
