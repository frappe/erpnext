import frappe
from frappe import _, bold
from frappe.utils import flt, get_link_to_form, getdate


class BundleVoucherLink:
	def __init__(self, doc):
		self.doc = doc

	def set_serial_and_batch_values(self, parent, row, qty_field=None):
		from erpnext.stock.utils import get_combine_datetime

		self.validate_not_linked_to_another_draft(parent, row)

		values_to_set = {"is_cancelled": 0}
		if not self.doc.voucher_no or self.doc.voucher_no != row.parent:
			values_to_set["voucher_no"] = row.parent

		if self.doc.voucher_type != parent.doctype:
			values_to_set["voucher_type"] = parent.doctype

		if not self.doc.voucher_detail_no or self.doc.voucher_detail_no != row.name:
			values_to_set["voucher_detail_no"] = row.name

		if row.get("doctype") == "Packed Item" and row.get("parent_detail_docname"):
			values_to_set["voucher_detail_no"] = row.get("parent_detail_docname")

		if parent.get("posting_date") and parent.get("posting_time"):
			posting_datetime = get_combine_datetime(parent.posting_date, parent.posting_time)
			if not self.doc.posting_datetime or self.doc.posting_datetime != posting_datetime:
				values_to_set["posting_datetime"] = posting_datetime

		if parent.doctype in [
			"Delivery Note",
			"Purchase Receipt",
			"Purchase Invoice",
			"Sales Invoice",
		] and parent.get("is_return"):
			return_ref_field = frappe.scrub(parent.doctype) + "_item"
			if parent.doctype == "Delivery Note":
				return_ref_field = "dn_detail"

			if row.get(return_ref_field):
				values_to_set["returned_against"] = row.get(return_ref_field)

		self.doc.db_set(values_to_set)
		values_to_set.pop("returned_against", None)
		frappe.db.set_value(
			"Serial and Batch Entry", {"parent": self.doc.name}, values_to_set, update_modified=False
		)

		self.doc.calculate_total_qty(save=True)

		# If user has changed the rate in the child table
		if self.doc.docstatus == 0 and self.doc.type_of_transaction == "Inward":
			self.doc.set_incoming_rate(parent=parent, row=row, save=True)

		if self.doc.docstatus == 0 and parent.get("is_return") and parent.is_new():
			self.reset_qty(row, qty_field=qty_field)

		self.doc.calculate_qty_and_amount(save=True)
		self.validate_quantity(row, qty_field=qty_field)

	def validate_not_linked_to_another_draft(self, parent, row):
		"""A draft voucher can't take over the bundle of another draft voucher."""
		if not (self.doc.voucher_type and self.doc.voucher_no):
			return

		if self.doc.voucher_type == parent.doctype and self.doc.voucher_no == row.parent:
			return

		if frappe.db.get_value(self.doc.voucher_type, self.doc.voucher_no, "docstatus") != 0:
			return

		frappe.throw(
			_(
				"Row #{0}: Serial and Batch Bundle {1} belongs to {2} {3}. Select or create another bundle."
			).format(
				row.idx,
				bold(self.doc.name),
				self.doc.voucher_type,
				get_link_to_form(self.doc.voucher_type, self.doc.voucher_no),
			)
		)

	def get_qty_field(self, row, qty_field=None) -> str:
		if not qty_field:
			qty_field = "qty"

		if row.get("doctype") == "Subcontracting Receipt Supplied Item":
			qty_field = "consumed_qty"
		elif row.get("doctype") == "Stock Entry Detail":
			qty_field = "transfer_qty"
		elif row.get("doctype") in ["Sales Invoice Item", "Purchase Invoice Item"] and qty_field == "qty":
			qty_field = "stock_qty"

		return qty_field

	def get_row_qty(self, row, qty_field) -> float:
		"""What the row holds in the units a package counts in."""
		if qty_field == "qty" and row.get("stock_qty"):
			return flt(row.get("stock_qty"))

		if qty_field == "rejected_qty":
			return flt(row.get(qty_field)) * flt(row.get("conversion_factor") or 1)

		return flt(row.get(qty_field))

	def reset_qty(self, row, qty_field=None):
		qty_field = self.get_qty_field(row, qty_field=qty_field)
		qty = abs(flt(self.get_row_qty(row, qty_field), self.doc.precision("total_qty")))

		idx = None
		while qty > 0:
			for d in self.doc.entries:
				row_qty = abs(flt(d.qty, d.precision("qty")))
				if row_qty >= qty:
					d.db_set("qty", qty if self.doc.type_of_transaction == "Inward" else qty * -1)
					qty = 0
					idx = d.idx
					break
				else:
					qty = flt(qty - row_qty, d.precision("qty"))
					idx = d.idx

		if idx and len(self.doc.entries) > idx:
			remove_rows = []
			for d in self.doc.entries:
				if d.idx > idx:
					remove_rows.append(d)

			for d in remove_rows:
				self.doc.entries.remove(d)

			self.doc.flags.ignore_links = True
			self.doc.save()

	def validate_quantity(self, row, qty_field=None):
		qty_field = self.get_qty_field(row, qty_field=qty_field)
		qty = self.get_row_qty(row, qty_field)

		precision = row.precision(qty_field)
		if abs(abs(flt(self.doc.total_qty, precision)) - abs(flt(qty, precision))) > 0.01:
			total_qty = frappe.format_value(abs(flt(self.doc.total_qty)), "Float", row)
			set_qty = frappe.format_value(abs(flt(qty)), "Float", row)
			self.doc.throw_error_message(
				_(
					"Total quantity {0} in the Serial and Batch Bundle {1} does not match with the quantity {2} for the Item {3} in the {4} # {5}"
				).format(
					total_qty,
					bold(self.doc.name),
					set_qty,
					bold(self.doc.item_code),
					self.doc.voucher_type,
					self.doc.voucher_no,
				)
			)

	def set_source_document_no(self):
		if self.doc.flags.ignore_validate_serial_batch:
			return

		if not self.doc.has_serial_no and not self.doc.has_batch_no:
			return

		if self.doc.total_qty <= 0:
			return

		if self.doc.has_serial_no:
			serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
			sn_table = frappe.qb.DocType("Serial No")
			(
				frappe.qb.update(sn_table)
				.set(sn_table.reference_doctype, self.doc.voucher_type)
				.set(sn_table.reference_name, self.doc.voucher_no)
				.set(sn_table.posting_date, getdate(self.doc.posting_datetime))
				.where((sn_table.name.isin(serial_nos)) & (sn_table.reference_name.isnull()))
			).run()

		if self.doc.has_batch_no:
			batch_nos = [d.batch_no for d in self.doc.entries if d.batch_no]
			batch_table = frappe.qb.DocType("Batch")
			(
				frappe.qb.update(batch_table)
				.set(batch_table.reference_doctype, self.doc.voucher_type)
				.set(batch_table.reference_name, self.doc.voucher_no)
				.where((batch_table.name.isin(batch_nos)) & (batch_table.reference_name.isnull()))
			).run()

	def remove_source_document_no(self):
		if not self.doc.has_serial_no and not self.doc.has_batch_no:
			return

		if self.doc.total_qty <= 0:
			return

		if self.doc.has_serial_no:
			serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
			sn_table = frappe.qb.DocType("Serial No")
			(
				frappe.qb.update(sn_table)
				.set(sn_table.reference_doctype, None)
				.set(sn_table.reference_name, None)
				.set(sn_table.posting_date, None)
				.where(
					(sn_table.name.isin(serial_nos))
					& (sn_table.reference_doctype == self.doc.voucher_type)
					& (sn_table.reference_name == self.doc.voucher_no)
					& (sn_table.posting_date == getdate(self.doc.posting_datetime))
				)
			).run()

		if self.doc.has_batch_no:
			batch_nos = [d.batch_no for d in self.doc.entries if d.batch_no]
			batch_table = frappe.qb.DocType("Batch")
			(
				frappe.qb.update(batch_table)
				.set(batch_table.reference_doctype, None)
				.set(batch_table.reference_name, None)
				.where(
					(batch_table.name.isin(batch_nos))
					& (batch_table.reference_doctype == self.doc.voucher_type)
					& (batch_table.reference_name == self.doc.voucher_no)
				)
			).run()

	def delink_serial_and_batch_bundle(self):
		sles = frappe.get_all("Stock Ledger Entry", filters={"serial_and_batch_bundle": self.doc.name})

		for sle in sles:
			frappe.db.set_value("Stock Ledger Entry", sle.name, "serial_and_batch_bundle", None)

	def delink_reference_from_voucher(self):
		or_filters = {"serial_and_batch_bundle": self.doc.name}

		fields = ["name", "serial_and_batch_bundle"]
		if self.doc.voucher_type == "Stock Reconciliation":
			fields = ["name", "current_serial_and_batch_bundle", "serial_and_batch_bundle"]
			or_filters["current_serial_and_batch_bundle"] = self.doc.name

		elif self.doc.voucher_type == "Purchase Receipt":
			fields = ["name", "rejected_serial_and_batch_bundle", "serial_and_batch_bundle"]
			or_filters["rejected_serial_and_batch_bundle"] = self.doc.name

		if (
			self.doc.voucher_type == "Subcontracting Receipt"
			and self.doc.voucher_detail_no
			and not frappe.db.exists("Subcontracting Receipt Item", self.doc.voucher_detail_no)
		):
			self.doc.voucher_type = "Subcontracting Receipt Supplied"

		vouchers = frappe.get_all(
			self.doc.child_table,
			fields=fields,
			filters={"docstatus": 0},
			or_filters=or_filters,
		)

		if not vouchers and self.doc.voucher_type == "Delivery Note":
			if frappe.db.exists("Packed Item", self.doc.voucher_detail_no):
				frappe.db.set_value(
					"Packed Item", self.doc.voucher_detail_no, "serial_and_batch_bundle", None
				)
			else:
				packed_items = frappe.get_all(
					"Packed Item",
					filters={
						"parent_detail_docname": self.doc.voucher_detail_no,
						"serial_and_batch_bundle": self.doc.name,
					},
					pluck="name",
				)

				for packed_item in packed_items:
					frappe.db.set_value("Packed Item", packed_item, "serial_and_batch_bundle", None)

			return

		for voucher in vouchers:
			if voucher.get("current_serial_and_batch_bundle"):
				frappe.db.set_value(
					self.doc.child_table, voucher.name, "current_serial_and_batch_bundle", None
				)
			elif voucher.get("rejected_serial_and_batch_bundle"):
				frappe.db.set_value(
					self.doc.child_table, voucher.name, "rejected_serial_and_batch_bundle", None
				)

			frappe.db.set_value(self.doc.child_table, voucher.name, "serial_and_batch_bundle", None)

	def delink_reference_from_batch(self):
		batches = frappe.get_all(
			"Batch",
			fields=["name"],
			filters={"reference_name": self.doc.name, "reference_doctype": "Serial and Batch Bundle"},
		)

		for batch in batches:
			frappe.db.set_value("Batch", batch.name, {"reference_name": None, "reference_doctype": None})
