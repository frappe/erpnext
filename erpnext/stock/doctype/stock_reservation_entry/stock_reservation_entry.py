# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt


class StockReservationEntry(Document):
	def validate(self) -> None:
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_amended_doc()
		self.validate_mandatory()
		self.validate_for_group_warehouse()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)
		self.validate_uom_is_integer()

	def before_submit(self) -> None:
		self.validate_reservation_based_on_qty()
		self.auto_reserve_serial_and_batch()
		self.validate_reservation_based_on_serial_and_batch()

	def on_submit(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def on_update_after_submit(self) -> None:
		self.can_be_updated()
		self.validate_uom_is_integer()
		self.validate_reservation_based_on_qty()
		self.validate_reservation_based_on_serial_and_batch()
		self.update_reserved_qty_in_voucher()
		self.update_status()
		self.reload()

	def on_cancel(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def validate_amended_doc(self) -> None:
		"""Raises exception if document is amended."""

		if self.amended_from:
			frappe.throw(
				_(
					f"Cannot amend {self.doctype} {frappe.bold(self.amended_from)}, please create a new one instead."
				)
			)

	def validate_mandatory(self) -> None:
		"""Raises exception if mandatory fields are not set."""

		mandatory = [
			"item_code",
			"warehouse",
			"voucher_type",
			"voucher_no",
			"voucher_detail_no",
			"available_qty",
			"voucher_qty",
			"stock_uom",
			"reserved_qty",
			"company",
		]
		for d in mandatory:
			if not self.get(d):
				frappe.throw(_("{0} is required").format(self.meta.get_label(d)))

	def validate_for_group_warehouse(self) -> None:
		"""Raises exception if `Warehouse` is a Group Warehouse."""

		if frappe.get_cached_value("Warehouse", self.warehouse, "is_group"):
			frappe.throw(
				_("Stock cannot be reserved in group warehouse {0}.").format(frappe.bold(self.warehouse)),
				title=_("Invalid Warehouse"),
			)

	def validate_uom_is_integer(self):
		if cint(frappe.db.get_value("UOM", self.stock_uom, "must_be_whole_number", cache=True)):
			if cint(self.reserved_qty) != flt(self.reserved_qty, self.precision("reserved_qty")):
				msg = f"Reserved Qty ({flt(self.reserved_qty, self.precision('reserved_qty'))}) cannot be a fraction. To allow this, disable '{frappe.bold(_('Must be Whole Number'))}' in UOM {frappe.bold(self.stock_uom)}."
				frappe.throw(_(msg))

	def validate_reservation_based_on_qty(self) -> None:
		"""Validates `Reserved Qty` when `Reservation Based On` is `Qty`."""

		if self.reservation_based_on == "Qty":
			if self.sb_entries:
				self.sb_entries.clear()

			self.validate_with_max_reserved_qty(self.reserved_qty)

	def auto_reserve_serial_and_batch(self) -> None:
		if (
			(self.get("_action") == "submit")
			and (self.has_serial_no or self.has_batch_no)
			and cint(frappe.db.get_single_value("Stock Settings", "auto_reserve_serial_and_batch"))
		):
			from erpnext.stock.doctype.batch.batch import get_available_batches
			from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward
			from erpnext.stock.serial_batch_bundle import get_serial_nos_batch

			self.reservation_based_on = "Serial and Batch"
			kwargs = frappe._dict(
				{
					"item_code": self.item_code,
					"warehouse": self.warehouse,
					"qty": abs(self.reserved_qty) or 0,
					"based_on": frappe.db.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
				}
			)

			serial_nos, batch_nos = [], []
			if self.has_serial_no:
				serial_nos = get_serial_nos_for_outward(kwargs)
			if self.has_batch_no:
				batch_nos = get_available_batches(kwargs)

			if serial_nos:
				serial_no_wise_batch = frappe._dict({})

				if self.has_batch_no:
					serial_no_wise_batch = get_serial_nos_batch(serial_nos)

				for serial_no in serial_nos:
					self.append(
						"sb_entries",
						{
							"serial_no": serial_no,
							"qty": 1,
							"batch_no": serial_no_wise_batch.get(serial_no),
							"warehouse": self.warehouse,
						},
					)
			elif batch_nos:
				for batch_no, batch_qty in batch_nos.items():
					self.append(
						"sb_entries",
						{
							"batch_no": batch_no,
							"qty": batch_qty,
							"warehouse": self.warehouse,
						},
					)

	def validate_reservation_based_on_serial_and_batch(self) -> None:
		"""Validates `Reserved Qty`, `Serial and Batch Nos` when `Reservation Based On` is `Serial and Batch`."""

		if self.reservation_based_on == "Serial and Batch":
			if not self.has_serial_no and not self.has_batch_no:
				if self.sb_entries:
					self.sb_entries.clear()

				frappe.throw(_("Please select Reservation Based On as Qty."))

			qty_to_be_reserved = 0

			for entry in self.sb_entries:
				if not entry.warehouse:
					frappe.throw(
						_(f"Row #{entry.idx}: Warehouse is mandatory for Item {frappe.bold(self.item_code)}.")
					)

				if self.has_serial_no and entry.qty != 1:
					frappe.throw(_(f"Row #{entry.idx}: Qty should be 1 for Serialized Item."))

				if self.has_batch_no:
					available_qty_to_reserve = get_available_qty_to_reserve(
						self.item_code, entry.warehouse, entry.batch_no, ignore_sre=self.name
					)

					if not available_qty_to_reserve or available_qty_to_reserve < 0:
						frappe.throw(
							_(
								f"Row #{entry.idx}: Stock not availabe to reserve for Item {frappe.bold(self.item_code)} against Batch {frappe.bold(entry.batch_no)} in Warehouse {frappe.bold(entry.warehouse)}."
							)
						)

					if available_qty_to_reserve < entry.qty:
						frappe.throw(
							_(
								f"Row #{entry.idx}: Qty should be less than or equal to Available Qty to Reserve (Actual Qty - Reserved Qty) {frappe.bold(available_qty_to_reserve)} for Iem {frappe.bold(self.item_code)} against Batch {frappe.bold(entry.batch_no)} in Warehouse {frappe.bold(entry.warehouse)}."
							)
						)

				qty_to_be_reserved += entry.qty

			if not qty_to_be_reserved:
				frappe.throw(
					_("Please select Serial/Batch No to reserve or change Reservation Based On to Qty.")
				)

			self.validate_with_max_reserved_qty(qty_to_be_reserved)

			if self.reservation_based_on == "Serial and Batch":
				self.db_set("reserved_qty", qty_to_be_reserved)

	def update_reserved_qty_in_voucher(
		self, reserved_qty_field: str = "stock_reserved_qty", update_modified: bool = True
	) -> None:
		"""Updates total reserved qty in the voucher."""

		item_doctype = "Sales Order Item" if self.voucher_type == "Sales Order" else None

		if item_doctype:
			sre = frappe.qb.DocType("Stock Reservation Entry")
			reserved_qty = (
				frappe.qb.from_(sre)
				.select(Sum(sre.reserved_qty))
				.where(
					(sre.docstatus == 1)
					& (sre.voucher_type == self.voucher_type)
					& (sre.voucher_no == self.voucher_no)
					& (sre.voucher_detail_no == self.voucher_detail_no)
				)
			).run(as_list=True)[0][0] or 0

			frappe.db.set_value(
				item_doctype,
				self.voucher_detail_no,
				reserved_qty_field,
				reserved_qty,
				update_modified=update_modified,
			)

	def update_status(self, status: str = None, update_modified: bool = True) -> None:
		"""Updates status based on Voucher Qty, Reserved Qty and Delivered Qty."""

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if self.reserved_qty == self.delivered_qty:
					status = "Delivered"
				elif self.delivered_qty and self.delivered_qty < self.reserved_qty:
					status = "Partially Delivered"
				elif self.reserved_qty == self.voucher_qty:
					status = "Reserved"
				else:
					status = "Partially Reserved"
			else:
				status = "Draft"

		frappe.db.set_value(self.doctype, self.name, "status", status, update_modified=update_modified)

	def can_be_updated(self) -> None:
		"""Raises an exception if `Stock Reservation Entry` is not allowed to be updated."""

		if self.status == "Delivered":
			frappe.throw(_(f"Delivered {self.doctype} cannot be updated, create a new one instead."))

	def validate_with_max_reserved_qty(self, qty_to_be_reserved: float) -> None:
		"""Validates `Reserved Qty` with `Max Reserved Qty`."""

		self.db_set(
			"available_qty",
			get_available_qty_to_reserve(self.item_code, self.warehouse, ignore_sre=self.name),
		)

		total_reserved_qty = get_sre_reserved_qty_for_voucher_detail_no(
			self.voucher_type, self.voucher_no, self.voucher_detail_no, ignore_sre=self.name
		)

		voucher_delivered_qty = 0
		if self.voucher_type == "Sales Order":
			delivered_qty, conversion_factor = frappe.db.get_value(
				"Sales Order Item", self.voucher_detail_no, ["delivered_qty", "conversion_factor"]
			)
			voucher_delivered_qty = flt(delivered_qty) * flt(conversion_factor)

		max_reserved_qty = min(
			self.available_qty, (self.voucher_qty - voucher_delivered_qty - total_reserved_qty)
		)

		if max_reserved_qty <= 0 and self.voucher_type == "Sales Order":
			msg = f"Item {frappe.bold(self.item_code)} is already delivered for Sales Order {frappe.bold(self.voucher_no)}."

			if self.docstatus == 1:
				self.cancel()
				return frappe.msgprint(_(msg))
			else:
				frappe.throw(_(msg))

		if qty_to_be_reserved > max_reserved_qty:
			frappe.throw(_(f"Cannot reserve more than {frappe.bold(max_reserved_qty)} {self.stock_uom}."))

		if qty_to_be_reserved <= self.delivered_qty:
			frappe.throw(_("Reserved Qty should be greater than Delivered Qty."))


def validate_stock_reservation_settings(voucher: object) -> None:
	"""Raises an exception if `Stock Reservation` is not enabled or `Voucher Type` is not allowed."""

	if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		frappe.throw(
			_("Please enable {0} in the {1}.").format(
				frappe.bold("Stock Reservation"), frappe.bold("Stock Settings")
			)
		)

	# Voucher types allowed for stock reservation
	allowed_voucher_types = ["Sales Order"]

	if voucher.doctype not in allowed_voucher_types:
		frappe.throw(
			_("Stock Reservation can only be created against {0}.").format(", ".join(allowed_voucher_types))
		)


def get_available_qty_to_reserve(
	item_code: str, warehouse: str, batch_no: str = None, ignore_sre=None
) -> float:
	"""Returns `Available Qty to Reserve (Actual Qty - Reserved Qty)` for Item, Warehouse and Batch combination."""

	available_qty = 0.0
	if batch_no:
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		available_qty = get_batch_qty(item_code=item_code, warehouse=warehouse, batch_no=batch_no)
	else:
		from erpnext.stock.utils import get_stock_balance

		available_qty = get_stock_balance(item_code, warehouse)

	if available_qty:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		query = frappe.qb.from_(sre).where(
			(sre.docstatus == 1)
			& (sre.item_code == item_code)
			& (sre.warehouse == warehouse)
			& (sre.reserved_qty >= sre.delivered_qty)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)

		if batch_no:
			sb_entry = frappe.qb.DocType("Serial and Batch Entry")
			query = (
				query.left_join(sb_entry)
				.on(sre.name == sb_entry.parent)
				.select(Sum(sb_entry.qty))
				.where(sb_entry.batch_no == batch_no)
			)
		else:
			query = query.select(Sum(sre.reserved_qty - sre.delivered_qty))

		if ignore_sre:
			query = query.where(sre.name != ignore_sre)

		reserved_qty = query.run()[0][0] or 0.0

		if reserved_qty:
			return available_qty - reserved_qty

	return available_qty


def get_stock_reservation_entries_for_voucher(
	voucher_type: str, voucher_no: str, voucher_detail_no: str = None, fields: list[str] = None
) -> list[dict]:
	"""Returns list of Stock Reservation Entries against a Voucher."""

	if not fields or not isinstance(fields, list):
		fields = [
			"name",
			"item_code",
			"warehouse",
			"voucher_detail_no",
			"reserved_qty",
			"delivered_qty",
			"stock_uom",
		]

	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.orderby(sre.creation)
	)

	for field in fields:
		query = query.select(sre[field])

	if voucher_detail_no:
		query = query.where(sre.voucher_detail_no == voucher_detail_no)

	return query.run(as_dict=True)


def get_sre_reserved_qty_details_for_item_and_warehouse(
	item_code_list: list, warehouse_list: list
) -> dict:
	"""Returns a dict like {("item_code", "warehouse"): "reserved_qty", ... }."""

	sre_details = {}

	if item_code_list and warehouse_list:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		sre_data = (
			frappe.qb.from_(sre)
			.select(
				sre.item_code,
				sre.warehouse,
				Sum(sre.reserved_qty - sre.delivered_qty).as_("reserved_qty"),
			)
			.where(
				(sre.docstatus == 1)
				& (sre.item_code.isin(item_code_list))
				& (sre.warehouse.isin(warehouse_list))
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
			.groupby(sre.item_code, sre.warehouse)
		).run(as_dict=True)

		if sre_data:
			sre_details = {(d["item_code"], d["warehouse"]): d["reserved_qty"] for d in sre_data}

	return sre_details


def get_sre_reserved_qty_for_item_and_warehouse(item_code: str, warehouse: str) -> float:
	"""Returns `Reserved Qty` for Item and Warehouse combination."""

	reserved_qty = 0.0

	if item_code and warehouse:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		return (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		).run(as_list=True)[0][0] or 0.0

	return reserved_qty


def get_sre_reserved_qty_details_for_voucher(voucher_type: str, voucher_no: str) -> dict:
	"""Returns a dict like {"voucher_detail_no": "reserved_qty", ... }."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	data = (
		frappe.qb.from_(sre)
		.select(
			sre.voucher_detail_no,
			(Sum(sre.reserved_qty) - Sum(sre.delivered_qty)).as_("reserved_qty"),
		)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.groupby(sre.voucher_detail_no)
	).run(as_list=True)

	return frappe._dict(data)


def get_sre_reserved_warehouses_for_voucher(
	voucher_type: str, voucher_no: str, voucher_detail_no: str = None
) -> list:
	"""Returns a list of warehouses where the stock is reserved for the provided voucher."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.select(sre.warehouse)
		.distinct()
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.orderby(sre.creation)
	)

	if voucher_detail_no:
		query = query.where(sre.voucher_detail_no == voucher_detail_no)

	warehouses = query.run(as_list=True)

	return [d[0] for d in warehouses] if warehouses else []


def get_sre_reserved_qty_for_voucher_detail_no(
	voucher_type: str, voucher_no: str, voucher_detail_no: str, ignore_sre=None
) -> float:
	"""Returns `Reserved Qty` against the Voucher."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.select(
			(Sum(sre.reserved_qty) - Sum(sre.delivered_qty)),
		)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.voucher_detail_no == voucher_detail_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
	)

	if ignore_sre:
		query = query.where(sre.name != ignore_sre)

	reserved_qty = query.run(as_list=True)

	return flt(reserved_qty[0][0])


def has_reserved_stock(voucher_type: str, voucher_no: str, voucher_detail_no: str = None) -> bool:
	"""Returns True if there is any Stock Reservation Entry for the given voucher."""

	if get_stock_reservation_entries_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, fields=["name"]
	):
		return True

	return False


@frappe.whitelist()
def cancel_stock_reservation_entries(
	voucher_type: str, voucher_no: str, voucher_detail_no: str = None, notify: bool = True
) -> None:
	"""Cancel Stock Reservation Entries for the given voucher."""

	sre_list = get_stock_reservation_entries_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, fields=["name"]
	)

	if sre_list:
		for sre in sre_list:
			frappe.get_doc("Stock Reservation Entry", sre.name).cancel()

		if notify:
			frappe.msgprint(_("Stock Reservation Entries Cancelled"), alert=True, indicator="red")
