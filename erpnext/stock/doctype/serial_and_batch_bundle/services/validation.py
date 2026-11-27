import collections

import frappe
from frappe import _, bold
from frappe.query_builder.functions import Coalesce
from frappe.utils import escape_html, get_link_to_form

from erpnext.stock.doctype.serial_and_batch_bundle.services.future_transactions import (
	BundleFutureTransactions,
)
from erpnext.stock.serial_batch_bundle.availability.reservations import get_serial_no_reservation
from erpnext.stock.serial_batch_bundle.availability.serial_nos import get_available_serial_nos
from erpnext.stock.serial_batch_identity import SerialBatchIdentity


class SerialNoDuplicateError(frappe.ValidationError):
	pass


class SerialNoWarehouseError(frappe.ValidationError):
	pass


class BundleValidation:
	def __init__(self, doc):
		self.doc = doc

	def validate_allow_to_set_serial_batch(self):
		if not frappe.db.get_single_value("Stock Settings", "enable_serial_and_batch_no_for_item"):
			frappe.throw(
				_(
					"Please check the 'Activate Serial and Batch No for Item' checkbox in the {0} to make Serial and Batch Bundle for the item."
				).format(get_link_to_form("Stock Settings", "Stock Settings")),
				title=_("Serial and Batch No for Item Disabled"),
			)

	def validate_voucher_detail_no(self):
		if self.doc.type_of_transaction not in ["Inward", "Outward"] or self.doc.voucher_type in [
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
		]:
			return

		if self.doc.voucher_type == "POS Invoice":
			if not frappe.db.exists("POS Invoice Item", self.doc.voucher_detail_no):
				frappe.throw(
					_("The serial and batch bundle {0} is not linked to {1} {2}").format(
						bold(self.doc.name), self.doc.voucher_type, bold(self.doc.voucher_no)
					)
				)

		elif not frappe.db.exists("Stock Ledger Entry", {"voucher_detail_no": self.doc.voucher_detail_no}):
			if self.doc.voucher_type in ["Delivery Note", "Sales Invoice"] and frappe.db.exists(
				"Packed Item", self.doc.voucher_detail_no
			):
				return

			frappe.throw(
				_("The serial and batch bundle {0} is not linked to {1} {2}").format(
					bold(self.doc.name), self.doc.voucher_type, bold(self.doc.voucher_no)
				)
			)

	def validate_voucher_no(self):
		if not (self.doc.voucher_type and self.doc.voucher_no):
			return

		if (
			self.doc.docstatus == 1
			and self.doc.voucher_no
			and not frappe.db.exists(self.doc.voucher_type, self.doc.voucher_no)
		):
			self.doc.throw_error_message(
				_("The {0} # {1} does not exist").format(self.doc.voucher_type, self.doc.voucher_no)
			)

		if self.doc.flags.ignore_voucher_validation:
			return

		if (
			self.doc.docstatus == 1
			and frappe.get_cached_value(self.doc.voucher_type, self.doc.voucher_no, "docstatus") != 1
		):
			self.doc.throw_error_message(
				_("The {0} # {1} should be submitted first.").format(
					self.doc.voucher_type, self.doc.voucher_no
				)
			)

	def validate_serial_and_batch_no(self):
		if self.doc.item_code and not self.doc.has_serial_no and not self.doc.has_batch_no:
			frappe.throw(_("The Item {0} does not have Serial No or Batch No").format(self.doc.item_code))

		serial_nos = []
		batch_nos = set()

		serial_batches = {}
		for row in self.doc.entries:
			if not row.qty and row.batch_no and not row.serial_no:
				if (
					self.doc.voucher_type == "Stock Reconciliation"
					and self.doc.type_of_transaction == "Inward"
				):
					continue

				frappe.throw(
					_("At row {0}: Qty is mandatory for the batch {1}").format(
						bold(row.idx), bold(SerialBatchIdentity("Batch").get_label(row.batch_no))
					)
				)

			if self.doc.has_serial_no and not row.serial_no:
				frappe.throw(
					_("At row {0}: Serial No is mandatory for Item {1}").format(
						bold(row.idx), bold(self.doc.item_code)
					),
					title=_("Serial No is mandatory"),
				)

			if self.doc.has_batch_no and not row.batch_no:
				frappe.throw(
					_("At row {0}: Batch No is mandatory for Item {1}").format(
						bold(row.idx), bold(self.doc.item_code)
					),
					title=_("Batch No is mandatory"),
				)

			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no:
				batch_nos.add(row.batch_no)

			if row.serial_no and row.batch_no and self.doc.type_of_transaction == "Outward":
				serial_batches.setdefault(row.serial_no, row.batch_no)

		if serial_nos:
			self.validate_incorrect_serial_nos(serial_nos)

		if batch_nos:
			self.validate_incorrect_batch_nos(list(batch_nos))

		if serial_batches:
			self.validate_serial_batch_no(serial_batches)

	def validate_incorrect_serial_nos(self, serial_nos):
		incorrect_serial_nos = frappe.get_all(
			"Serial No",
			filters={"name": ("in", serial_nos), "item_code": ("!=", self.doc.item_code)},
			pluck="serial_no",
		)

		if incorrect_serial_nos:
			incorrect_serial_nos = escape_html(", ".join(incorrect_serial_nos))
			self.doc.throw_error_message(
				_("Serial Nos {0} does not belong to Item {1}").format(
					bold(incorrect_serial_nos), bold(self.doc.item_code)
				)
			)

	def validate_incorrect_batch_nos(self, batch_nos):
		incorrect_batch_nos = frappe.get_all(
			"Batch", filters={"name": ("in", batch_nos), "item": ("!=", self.doc.item_code)}, pluck="batch_id"
		)

		if incorrect_batch_nos:
			incorrect_batch_nos = escape_html(", ".join(incorrect_batch_nos))
			self.doc.throw_error_message(
				_("Batch Nos {0} does not belong to Item {1}").format(
					bold(incorrect_batch_nos), bold(self.doc.item_code)
				)
			)

	def validate_serial_batch_no(self, serial_batches):
		correct_batches = frappe._dict(
			frappe.get_all(
				"Serial No",
				filters={"name": ("in", list(serial_batches.keys()))},
				fields=["name", "batch_no"],
				as_list=True,
			)
		)

		for serial_no, batch_no in serial_batches.items():
			if correct_batches.get(serial_no) and correct_batches.get(serial_no) != batch_no:
				serial_number = SerialBatchIdentity("Serial No").get_label(serial_no)
				batch_number = SerialBatchIdentity("Batch").get_label(batch_no)
				self.doc.throw_error_message(
					_("Serial No {0} does not belong to Batch No {1}").format(
						bold(serial_number), bold(batch_number)
					)
				)

	def validate_duplicate_serial_and_batch_no(self):
		serial_nos = []
		batch_nos = []

		for row in self.doc.entries:
			if row.serial_no:
				serial_nos.append(row.serial_no)

			if row.batch_no and not row.serial_no:
				batch_nos.append(row.batch_no)

		if serial_nos:
			for key, value in collections.Counter(serial_nos).items():
				if value > 1:
					self.doc.throw_error_message(
						_("Duplicate Serial No {0} found").format(
							SerialBatchIdentity("Serial No").get_label(key)
						)
					)

		if batch_nos:
			for key, value in collections.Counter(batch_nos).items():
				if value > 1:
					self.doc.throw_error_message(
						_("Duplicate Batch No {0} found").format(SerialBatchIdentity("Batch").get_label(key))
					)

	def allow_existing_serial_nos(self):
		if self.doc.type_of_transaction == "Outward" or not self.doc.has_serial_no:
			return

		if frappe.get_single_value("Stock Settings", "allow_existing_serial_no"):
			return

		if self.doc.voucher_type not in ["Purchase Receipt", "Purchase Invoice", "Stock Entry"]:
			return

		if self.doc.voucher_type == "Stock Entry" and frappe.get_cached_value(
			"Stock Entry", self.doc.voucher_no, "purpose"
		) in ["Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture"]:
			return

		serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
		if not serial_nos:
			return

		entry = frappe.qb.DocType("Serial and Batch Entry")
		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		query = (
			frappe.qb.from_(entry)
			.join(bundle)
			.on(bundle.name == entry.parent)
			.select(entry.serial_no, entry.parent, bundle.voucher_type, bundle.voucher_no)
			.where((entry.serial_no.isin(serial_nos)) & (entry.docstatus == 1) & (entry.qty < 0))
		)
		if self.doc.docstatus == 0:
			# a serial no still in stock may be moving (e.g. a batch split), so check it on submit
			serial_no = frappe.qb.DocType("Serial No")
			query = (
				query.join(serial_no)
				.on(serial_no.name == entry.serial_no)
				.where(Coalesce(serial_no.warehouse, "") == "")
			)

		data = query.run(as_dict=True)

		# a serial no issued by this same voucher is moved within it, not received again
		moved = {
			row.serial_no
			for row in data
			if row.voucher_type == self.doc.voucher_type and row.voucher_no == self.doc.voucher_no
		}
		data = [row for row in data if row.serial_no not in moved]

		note = "<br><br> <b>Note</b>:<br>"
		for row in data:
			frappe.throw(
				_(
					"You cannot process the serial number {0} as it has already been used in the SABB {1}. {2} If you want to inward the same serial number multiple times, then enable 'Allow existing Serial No to be Manufactured/Received again' in the {3}"
				).format(
					SerialBatchIdentity("Serial No").get_label(row.serial_no),
					get_link_to_form("Serial and Batch Bundle", row.parent),
					note,
					get_link_to_form("Stock Settings", "Stock Settings"),
				)
			)

	def validate_serial_nos_duplicate(self):
		# Don't inward same serial number multiple times
		if self.doc.voucher_type in ["POS Invoice", "Pick List"]:
			return

		if not self.doc.warehouse:
			return

		if self.doc.voucher_type in ["Stock Reconciliation", "Stock Entry"] and self.doc.docstatus != 1:
			return

		if not (self.doc.has_serial_no and self.doc.type_of_transaction == "Inward"):
			return

		serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
		kwargs = frappe._dict(
			{
				"item_code": self.doc.item_code,
				"posting_datetime": self.doc.posting_datetime,
				"serial_nos": serial_nos,
				"check_serial_nos": True,
			}
		)

		if self.doc.docstatus == 1:
			kwargs["ignore_voucher_detail_no"] = self.doc.voucher_detail_no
			kwargs["voucher_no"] = self.doc.voucher_no

		available_serial_nos = get_available_serial_nos(kwargs)
		for data in available_serial_nos:
			if data.serial_no in serial_nos:
				serial_number = SerialBatchIdentity("Serial No").get_label(data.serial_no)
				self.doc.throw_error_message(
					_("Serial No {0} is already present in the warehouse {1}.").format(
						bold(serial_number), bold(data.warehouse)
					),
					SerialNoDuplicateError,
				)

		if (
			self.doc.voucher_type == "Stock Entry"
			and self.doc.type_of_transaction == "Inward"
			and frappe.get_cached_value("Stock Entry", self.doc.voucher_no, "purpose")
			in ["Manufacture", "Repack"]
		):
			serial_nos = frappe.get_all(
				"Serial No", filters={"name": ("in", serial_nos), "status": "Delivered"}, pluck="serial_no"
			)

			if serial_nos:
				if len(serial_nos) == 1:
					frappe.throw(
						_(
							"Serial No {0} is already Delivered. You cannot use it again in Manufacture / Repack entry."
						).format(bold(escape_html(serial_nos[0])))
					)
				else:
					frappe.throw(
						_(
							"Serial Nos {0} are already Delivered. You cannot use them again in Manufacture / Repack entry."
						).format(bold(escape_html(", ".join(serial_nos))))
					)

	def validate_serial_no_status(self):
		serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]
		invalid_serial_nos = frappe.get_all(
			"Serial No",
			filters={
				"name": ("in", serial_nos),
				"warehouse": ("!=", self.doc.warehouse),
			},
			pluck="serial_no",
		)

		if invalid_serial_nos:
			msg = _(
				"You cannot outward the following {0} as they are either Delivered, Inactive or located in a different warehouse."
			).format(_("Serial Nos") if len(invalid_serial_nos) > 1 else _("Serial No"))
			msg += "<hr>"
			msg += escape_html(", ".join(invalid_serial_nos))
			frappe.throw(msg)

	def validate_serial_nos_inventory(self):
		if not (self.doc.has_serial_no and self.doc.type_of_transaction == "Outward"):
			return

		if self.doc.voucher_type == "Stock Reconciliation":
			serial_nos, batches = BundleFutureTransactions(self.doc).get_serial_nos_for_validate()
		else:
			serial_nos = [d.serial_no for d in self.doc.entries if d.serial_no]

		if not serial_nos:
			return

		kwargs = {
			"item_code": self.doc.item_code,
			"warehouse": self.doc.warehouse,
			"check_serial_nos": True,
			"serial_nos": serial_nos,
			"sabb_voucher_type": self.doc.voucher_type,
			"sabb_voucher_no": self.doc.voucher_no,
			"sabb_voucher_detail_no": self.doc.voucher_detail_no,
		}

		if self.doc.voucher_type == "POS Invoice":
			kwargs["ignore_voucher_nos"] = [self.doc.voucher_no]

		if self.doc.voucher_type == "Stock Reconciliation":
			kwargs.update(
				{
					"voucher_no": self.doc.voucher_no,
					"posting_datetime": self.doc.posting_datetime,
				}
			)

		available_serial_nos = get_available_serial_nos(frappe._dict(kwargs))

		serial_no_warehouse = {}
		for data in available_serial_nos:
			if data.serial_no not in serial_nos:
				continue

			serial_no_warehouse[data.serial_no] = data.warehouse

		for serial_no in serial_nos:
			if (
				not serial_no_warehouse.get(serial_no)
				or serial_no_warehouse.get(serial_no) != self.doc.warehouse
			):
				serial_number = SerialBatchIdentity("Serial No").get_label(serial_no)
				reservation = get_serial_no_reservation(self.doc.item_code, serial_no, self.doc.warehouse)
				if reservation:
					self.doc.throw_error_message(
						_(
							"Serial No {0} is in warehouse {1} but is reserved for {2} {3} via {4}. Please use an unreserved serial number or cancel the reservation."
						).format(
							bold(serial_number),
							bold(self.doc.warehouse),
							reservation.voucher_type,
							bold(reservation.voucher_no),
							get_link_to_form("Stock Reservation Entry", reservation.name),
						),
						SerialNoWarehouseError,
					)
				else:
					self.doc.throw_error_message(
						_("Serial No {0} is not present in the warehouse {1}.").format(
							bold(serial_number), bold(self.doc.warehouse)
						),
						SerialNoWarehouseError,
					)

	def validate_serial_and_batch_data(self):
		if not self.doc.voucher_no:
			frappe.throw(_("Voucher No is mandatory"))

	def validate_submitted_with_its_voucher(self):
		if self.doc.flags.ignore_voucher_validation or self.doc.type_of_transaction not in (
			"Inward",
			"Outward",
		):
			return

		if not self.doc.voucher_no or self.doc.voucher_type in (
			"Installation Note",
			"Job Card",
			"Maintenance Schedule",
			"Pick List",
			"POS Invoice",
		):
			return

		if frappe.db.get_value(self.doc.voucher_type, self.doc.voucher_no, "docstatus") != 1:
			return

		if not frappe.db.exists(
			"Stock Ledger Entry",
			{"serial_and_batch_bundle": self.doc.name, "voucher_no": self.doc.voucher_no, "is_cancelled": 0},
		):
			frappe.throw(
				_(
					"Serial and Batch Bundle {0} is not posted by {1} {2}. A bundle is submitted with the transaction it belongs to."
				).format(bold(self.doc.name), self.doc.voucher_type, bold(self.doc.voucher_no))
			)

	def validate_docstatus(self):
		for row in self.doc.entries:
			if row.docstatus != 1:
				frappe.throw(
					_("At Row {0}: In Serial and Batch Bundle {1} must have docstatus as 1 and not 0").format(
						bold(row.idx), bold(self.doc.name)
					)
				)

	def validate_voucher_no_docstatus(self):
		if self.doc.is_cancelled:
			return

		if self.doc.voucher_type == "POS Invoice":
			return

		child_doctype = self.doc.voucher_type + " Item"
		mapper = {
			"Asset Capitalization": "Asset Capitalization Stock Item",
			"Asset Repair": "Asset Repair Consumed Item",
			"Stock Entry": "Stock Entry Detail",
		}.get(self.doc.voucher_type)

		if mapper:
			child_doctype = mapper

		if self.doc.voucher_type == "Delivery Note" and not frappe.db.exists(
			"Delivery Note Item", self.doc.voucher_detail_no
		):
			child_doctype = "Packed Item"

		elif self.doc.voucher_type == "Sales Invoice" and not frappe.db.exists(
			"Sales Invoice Item", self.doc.voucher_detail_no
		):
			child_doctype = "Packed Item"

		elif self.doc.voucher_type == "Subcontracting Receipt" and not frappe.db.exists(
			"Subcontracting Receipt Item", self.doc.voucher_detail_no
		):
			child_doctype = "Subcontracting Receipt Supplied Item"

		if (
			frappe.db.get_value(self.doc.voucher_type, self.doc.voucher_no, "docstatus") == 1
			and self.doc.voucher_detail_no
			and frappe.db.exists(child_doctype, self.doc.voucher_detail_no)
		):
			frappe.throw(
				_("The {0} {1} is in submitted state, please cancel it first").format(
					self.doc.voucher_type, bold(self.doc.voucher_no)
				)
			)
