import frappe
from frappe import _, bold
from frappe.utils import flt, get_link_to_form

from erpnext.stock.serial_batch_bundle.bundle_entries import add_picked_batches, get_serial_nos
from erpnext.stock.serial_batch_bundle.creation import SerialBatchCreation
from erpnext.stock.serial_batch_bundle.serial_no_status import (
	set_batch_no_in_serial_nos,
	update_serial_no_status,
	update_serial_no_status_for_stock_reco,
)
from erpnext.stock.serial_batch_bundle.valuation import is_rejected


class SerialBatchBundle:
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.set_item_details()
		self.process_serial_and_batch_bundle()
		if self.sle.is_cancelled:
			self.delink_serial_and_batch_bundle()

		self.post_process()

	def process_serial_and_batch_bundle(self):
		if self.item_details.has_serial_no:
			self.process_serial_no()
		elif self.item_details.has_batch_no:
			self.process_batch_no()

	def set_item_details(self):
		fields = [
			"has_batch_no",
			"has_serial_no",
			"item_name",
			"item_group",
			"serial_no_series",
			"create_new_batch",
			"batch_number_series",
		]

		self.item_details = frappe.get_cached_value("Item", self.sle.item_code, fields, as_dict=1)

	def process_serial_no(self):
		if (
			not self.sle.is_cancelled
			and not self.sle.serial_and_batch_bundle
			and self.item_details.has_serial_no == 1
		):
			self.make_serial_batch_no_bundle()
		elif not self.sle.is_cancelled:
			self.validate_item_and_warehouse()

	def is_material_transfer(self):
		allowed_types = [
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
		]

		if (
			self.sle.voucher_type == "Stock Entry"
			and not self.sle.is_cancelled
			and frappe.get_cached_value("Stock Entry", self.sle.voucher_no, "purpose") in allowed_types
		):
			return True

	def get_transit_package(self) -> str | None:
		if self.sle.is_cancelled or self.sle.voucher_type not in ["Delivery Note", "Sales Invoice"]:
			return None

		return frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_no": self.sle.voucher_no,
				"voucher_detail_no": self.sle.voucher_detail_no,
				"item_code": self.sle.item_code,
				"actual_qty": ("<", 0),
				"is_cancelled": 0,
				"serial_and_batch_bundle": ("is", "set"),
			},
			"serial_and_batch_bundle",
			order_by="creation desc",
		)

	def make_serial_batch_no_bundle_for_material_transfer(self, bundle):
		from erpnext.controllers.stock_controller import make_bundle_for_material_transfer

		if not bundle:
			return

		new_bundle_id = make_bundle_for_material_transfer(
			is_new=False,
			docstatus=1,
			voucher_type=self.sle.voucher_type,
			voucher_no=self.sle.voucher_no,
			serial_and_batch_bundle=bundle,
			warehouse=self.sle.warehouse,
			type_of_transaction="Inward" if self.sle.actual_qty > 0 else "Outward",
			do_not_submit=0,
		)
		self.sle.db_set({"serial_and_batch_bundle": new_bundle_id})

	def make_serial_batch_no_bundle(self):
		if self.sle.actual_qty > 0 and (transit_package := self.get_transit_package()):
			self.make_serial_batch_no_bundle_for_material_transfer(transit_package)

			if not self.is_packed_entry():
				frappe.db.set_value(
					self.child_doctype,
					self.sle.voucher_detail_no,
					"serial_and_batch_bundle",
					self.sle.serial_and_batch_bundle,
				)

			return

		self.validate_item()
		if self.sle.actual_qty > 0 and self.is_material_transfer():
			self.make_serial_batch_no_bundle_for_material_transfer(
				frappe.db.get_value(
					"Stock Entry Detail", self.sle.voucher_detail_no, "serial_and_batch_bundle"
				)
			)
			return

		sn_doc = SerialBatchCreation(
			{
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"posting_datetime": self.sle.posting_datetime,
				"voucher_type": self.sle.voucher_type,
				"voucher_no": self.sle.voucher_no,
				"voucher_detail_no": self.sle.voucher_detail_no,
				"qty": self.sle.actual_qty,
				"avg_rate": self.sle.incoming_rate,
				"total_amount": flt(self.sle.actual_qty) * flt(self.sle.incoming_rate),
				"type_of_transaction": "Inward" if self.sle.actual_qty > 0 else "Outward",
				"company": self.company,
				"is_rejected": self.is_rejected_entry(),
				"is_packed": self.is_packed_entry(),
				"make_bundle_from_sle": 1,
				"sle": self.sle,
				**self.get_entries_held_by_voucher(),
			}
		).make_serial_and_batch_bundle()

		self.set_serial_and_batch_bundle(sn_doc)

	def get_entries_held_by_voucher(self):
		"""Serial nos and batch qty that draft bundles on this voucher's rows hold, to skip when picking."""
		if self.sle.actual_qty > 0:
			return {}

		bundle = frappe.qb.DocType("Serial and Batch Bundle")
		entry = frappe.qb.DocType("Serial and Batch Entry")
		entries = (
			frappe.qb.from_(bundle)
			.inner_join(entry)
			.on(entry.parent == bundle.name)
			.select(entry.serial_no, entry.batch_no, entry.qty, bundle.warehouse)
			.where(
				(
					bundle.name.isin(self.get_bundles_on_voucher_rows(self.child_doctype))
					| bundle.name.isin(self.get_bundles_on_voucher_rows("Packed Item"))
				)
				& (bundle.item_code == self.item_code)
				& (bundle.type_of_transaction == "Outward")
				& (bundle.docstatus == 0)
			)
		).run(as_dict=True)

		held_batches = frappe._dict()
		add_picked_batches(held_batches, entries)

		return {
			"ignore_serial_nos": [row.serial_no for row in entries if row.serial_no],
			"already_picked_batches": held_batches,
		}

	def get_bundles_on_voucher_rows(self, doctype):
		row = frappe.qb.DocType(doctype)
		return (
			frappe.qb.from_(row)
			.select(row.serial_and_batch_bundle)
			.where((row.parenttype == self.sle.voucher_type) & (row.parent == self.sle.voucher_no))
		)

	def validate_actual_qty(self, sn_doc):
		link = get_link_to_form("Serial and Batch Bundle", sn_doc.name)

		condition = {
			"Inward": self.sle.actual_qty > 0,
			"Outward": self.sle.actual_qty < 0,
		}.get(sn_doc.type_of_transaction)

		if not condition and self.sle.actual_qty:
			correct_type = "Inward"
			if sn_doc.type_of_transaction == "Inward":
				correct_type = "Outward"

			msg = _(
				"The type of transaction of Serial and Batch Bundle {0} is {1} but as per the Actual Qty {2} for the item {3} in the {4} {5} the type of transaction should be {6}"
			).format(
				link,
				bold(_(sn_doc.type_of_transaction)),
				self.sle.actual_qty,
				bold(self.sle.item_code),
				_(self.sle.voucher_type),
				self.sle.voucher_no,
				bold(_(correct_type)),
			)
			frappe.throw(msg, title=_("Incorrect Type of Transaction"))

		precision = sn_doc.precision("total_qty")
		if self.sle.actual_qty and flt(sn_doc.total_qty, precision) != flt(self.sle.actual_qty, precision):
			msg = _(
				"Total qty {0} of Serial and Batch Bundle {1} is not equal to Actual Qty {2} in the {3} {4}"
			).format(
				flt(sn_doc.total_qty, precision),
				link,
				flt(self.sle.actual_qty, precision),
				_(self.sle.voucher_type),
				self.sle.voucher_no,
			)
			frappe.throw(msg)

	def validate_item(self):
		hints = []
		if self.sle.actual_qty > 0:
			if not self.item_details.has_batch_no and not self.item_details.has_serial_no:
				hints.append(_("Item {0} is not a batch or serial no item").format(self.item_code))

			if self.item_details.has_serial_no and not self.item_details.serial_no_series:
				hints.append(
					_(
						"If you want auto pick serial bundle, then kindly set Serial No Series in Item {0}"
					).format(self.item_code)
				)

			if (
				self.item_details.has_batch_no
				and not self.item_details.batch_number_series
				and not frappe.get_single_value("Stock Settings", "naming_series_prefix")
			):
				hints.append(
					_(
						"If you want auto pick batch bundle, then kindly set Batch Number Series in Item {0}"
					).format(self.item_code)
				)

		elif self.sle.actual_qty < 0:
			if not frappe.get_single_value(
				"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"
			):
				hints.append(
					_(
						"If you want auto pick serial/batch bundle, then kindly enable 'Auto Create Serial and Batch Bundle' in Stock Settings."
					)
				)

		if hints:
			msg = _("Serial and Batch Bundle not set for item {0} in warehouse {1}").format(
				self.item_code, self.warehouse
			)
			frappe.throw(". ".join([msg, *hints]))

	def set_serial_and_batch_bundle(self, sn_doc):
		self.sle.auto_created_serial_and_batch_bundle = 1
		self.sle.db_set({"serial_and_batch_bundle": sn_doc.name, "auto_created_serial_and_batch_bundle": 1})

		if sn_doc.is_rejected:
			frappe.db.set_value(
				self.child_doctype,
				self.sle.voucher_detail_no,
				"rejected_serial_and_batch_bundle",
				sn_doc.name,
			)
		else:
			values_to_update = {
				"serial_and_batch_bundle": sn_doc.name,
			}

			if self.sle.actual_qty < 0 and self.is_material_transfer():
				basic_rate = flt(sn_doc.avg_rate)
				ste_detail = frappe.db.get_value(
					"Stock Entry Detail",
					self.sle.voucher_detail_no,
					["additional_cost", "landed_cost_voucher_amount", "transfer_qty"],
					as_dict=True,
				)

				additional_cost = 0.0

				if ste_detail:
					additional_cost = (
						flt(ste_detail.additional_cost) + flt(ste_detail.landed_cost_voucher_amount)
					) / flt(ste_detail.transfer_qty)

				values_to_update["basic_rate"] = basic_rate
				values_to_update["valuation_rate"] = basic_rate + additional_cost

			if not frappe.get_single_value(
				"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle"
			):
				if sn_doc.has_serial_no:
					serial_numbers = frappe.get_all(
						"Serial and Batch Entry",
						filters={"parent": sn_doc.name},
						pluck="serial_no.serial_no",
						order_by="idx",
					)
					values_to_update["serial_no"] = "\n".join(serial_numbers)
				elif sn_doc.has_batch_no and len(sn_doc.entries) == 1:
					values_to_update["batch_no"] = sn_doc.entries[0].batch_no

			doctype = self.child_doctype
			name = self.sle.voucher_detail_no
			if sn_doc.is_packed:
				doctype = "Packed Item"
				name = frappe.db.get_value(
					"Packed Item",
					{
						"parent_detail_docname": sn_doc.voucher_detail_no,
						"item_code": self.sle.item_code,
						"serial_and_batch_bundle": ("is", "not set"),
					},
					"name",
				)

			frappe.db.set_value(doctype, name, values_to_update)

	@property
	def child_doctype(self):
		child_doctype = self.sle.voucher_type + " Item"

		if self.sle.voucher_type == "Subcontracting Receipt" and self.sle.dependant_sle_voucher_detail_no:
			child_doctype = "Subcontracting Receipt Supplied Item"

		if self.sle.voucher_type == "Stock Entry":
			child_doctype = "Stock Entry Detail"

		if self.sle.voucher_type == "Asset Capitalization":
			child_doctype = "Asset Capitalization Stock Item"

		if self.sle.voucher_type == "Asset Repair":
			child_doctype = "Asset Repair Consumed Item"

		return child_doctype

	def is_rejected_entry(self):
		return is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse)

	def is_packed_entry(self):
		if self.sle.voucher_type in ["Delivery Note", "Sales Invoice"]:
			item_code = frappe.db.get_value(
				self.sle.voucher_type + " Item",
				self.sle.voucher_detail_no,
				"item_code",
			)

			if item_code != self.sle.item_code:
				return frappe.db.get_value("Item", item_code, "is_stock_item") == 0

		return False

	def process_batch_no(self):
		if (
			not self.sle.is_cancelled
			and not self.sle.serial_and_batch_bundle
			and self.item_details.has_batch_no == 1
			and (
				(self.item_details.create_new_batch and self.sle.actual_qty > 0)
				or (
					frappe.get_single_value(
						"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"
					)
					and self.sle.actual_qty < 0
				)
				or (self.sle.actual_qty > 0 and self.get_transit_package())
			)
		):
			self.make_serial_batch_no_bundle()
		elif not self.sle.is_cancelled:
			self.validate_item_and_warehouse()

	def validate_item_and_warehouse(self):
		if self.sle.serial_and_batch_bundle and not frappe.db.exists(
			"Serial and Batch Bundle",
			{
				"name": self.sle.serial_and_batch_bundle,
				"item_code": self.item_code,
				"warehouse": self.warehouse,
				"voucher_no": self.sle.voucher_no,
			},
		):
			frappe.throw(
				_(
					"The Serial and Batch Bundle {0} does not belong to Item {1} or Warehouse {2} or {3} no {4}"
				).format(
					bold(self.sle.serial_and_batch_bundle),
					bold(self.item_code),
					bold(self.warehouse),
					_(self.sle.voucher_type),
					bold(self.sle.voucher_no),
				)
			)

	def delink_serial_and_batch_bundle(self):
		if self.is_pos_or_asset_repair_transaction():
			return

		update_values = {
			"serial_and_batch_bundle": "",
		}

		if is_rejected(self.sle.voucher_type, self.sle.voucher_detail_no, self.sle.warehouse):
			update_values["rejected_serial_and_batch_bundle"] = ""

		frappe.db.set_value(self.child_doctype, self.sle.voucher_detail_no, update_values)
		if self.child_doctype == "Delivery Note":
			frappe.db.set_value(
				"Packed Item", {"parent_detail_docname": self.sle.voucher_detail_no}, update_values
			)

		frappe.db.set_value(
			"Serial and Batch Bundle",
			{"voucher_no": self.sle.voucher_no, "voucher_type": self.sle.voucher_type},
			{"is_cancelled": 1},
		)

		frappe.db.set_value(
			"Serial and Batch Entry",
			{"voucher_no": self.sle.voucher_no, "voucher_type": self.sle.voucher_type},
			{"is_cancelled": 1},
		)

		if self.sle.serial_and_batch_bundle:
			frappe.get_cached_doc(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle
			).validate_serial_and_batch_inventory()

	def post_process(self):
		if not self.sle.serial_and_batch_bundle and not self.sle.serial_no and not self.sle.batch_no:
			return

		if self.sle.serial_and_batch_bundle:
			docstatus = frappe.get_cached_value(
				"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "docstatus"
			)

			if docstatus == 0:
				self.submit_serial_and_batch_bundle()

			if (
				frappe.db.count(
					"Serial and Batch Entry", {"parent": self.sle.serial_and_batch_bundle, "docstatus": 0}
				)
				> 0
			) and not self.sle.is_cancelled:
				frappe.throw(
					_("Serial and Batch Bundle {0} is not submitted").format(
						bold(self.sle.serial_and_batch_bundle)
					)
				)

		if self.item_details.has_serial_no == 1:
			self.set_warehouse_and_status_in_serial_nos()

		if (
			self.sle.actual_qty > 0
			and self.item_details.has_serial_no == 1
			and self.item_details.has_batch_no == 1
		):
			set_batch_no_in_serial_nos(self.sle.serial_and_batch_bundle)

		if self.sle.is_cancelled and self.sle.serial_and_batch_bundle:
			self.cancel_serial_and_batch_bundle()

	def cancel_serial_and_batch_bundle(self):
		if self.is_pos_or_asset_repair_transaction():
			return

		doc = frappe.get_cached_doc("Serial and Batch Bundle", self.sle.serial_and_batch_bundle)
		if doc.docstatus == 1:
			doc.cancel()

	def is_pos_or_asset_repair_transaction(self):
		voucher_type = frappe.get_cached_value(
			"Serial and Batch Bundle", self.sle.serial_and_batch_bundle, "voucher_type"
		)

		if (
			self.sle.voucher_type == "Sales Invoice"
			and self.sle.serial_and_batch_bundle
			and (
				voucher_type == "POS Invoice"
				or frappe.get_cached_value("Sales Invoice", self.sle.voucher_no, "is_consolidated")
			)
		):
			return True

		if (
			self.sle.voucher_type == "Stock Entry"
			and self.sle.serial_and_batch_bundle
			and voucher_type == "Asset Repair"
		):
			return True

	def submit_serial_and_batch_bundle(self):
		doc = frappe.get_doc("Serial and Batch Bundle", self.sle.serial_and_batch_bundle)
		if self.sle.voucher_detail_no and doc.voucher_detail_no != self.sle.voucher_detail_no:
			doc.voucher_detail_no = self.sle.voucher_detail_no

		self.validate_actual_qty(doc)

		doc.flags.ignore_voucher_validation = True
		doc.submit()

	def set_warehouse_and_status_in_serial_nos(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as get_parsed_serial_nos

		if self.sle.auto_created_serial_and_batch_bundle and self.sle.actual_qty > 0:
			return

		serial_nos = get_serial_nos(self.sle.serial_and_batch_bundle)
		if not self.sle.serial_and_batch_bundle and self.sle.serial_no:
			serial_nos = get_parsed_serial_nos(self.sle.serial_no)

		if not serial_nos:
			return

		if self.sle.voucher_type == "Stock Reconciliation" and self.sle.actual_qty > 0:
			update_serial_no_status_for_stock_reco(serial_nos)
			return

		update_serial_no_status(self.sle, serial_nos)
