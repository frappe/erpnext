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
		self.set_reservation_based_on()
		self.validate_reservation_based_on_qty()
		self.auto_reserve_serial_and_batch()
		self.validate_reservation_based_on_serial_and_batch()

	def on_submit(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_reserved_qty_in_pick_list()
		self.update_status()

	def on_update_after_submit(self) -> None:
		self.can_be_updated()
		self.validate_uom_is_integer()
		self.set_reservation_based_on()
		self.validate_reservation_based_on_qty()
		self.validate_reservation_based_on_serial_and_batch()
		self.update_reserved_qty_in_voucher()
		self.update_status()
		self.reload()

	def on_cancel(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_reserved_qty_in_pick_list()
		self.update_status()

	def validate_amended_doc(self) -> None:
		"""Raises an exception if document is amended."""

		if self.amended_from:
			msg = _("Cannot amend {0} {1}, please create a new one instead.").format(
				self.doctype, frappe.bold(self.amended_from)
			)
			frappe.throw(msg)

	def validate_mandatory(self) -> None:
		"""Raises an exception if mandatory fields are not set."""

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
				msg = _("{0} is required").format(self.meta.get_label(d))
				frappe.throw(msg)

	def validate_for_group_warehouse(self) -> None:
		"""Raises an exception if `Warehouse` is a Group Warehouse."""

		if frappe.get_cached_value("Warehouse", self.warehouse, "is_group"):
			msg = _("Stock cannot be reserved in group warehouse {0}.").format(frappe.bold(self.warehouse))
			frappe.throw(msg, title=_("Invalid Warehouse"))

	def validate_uom_is_integer(self) -> None:
		"""Validates `Reserved Qty` with Stock UOM."""

		if cint(frappe.db.get_value("UOM", self.stock_uom, "must_be_whole_number", cache=True)):
			if cint(self.reserved_qty) != flt(self.reserved_qty, self.precision("reserved_qty")):
				msg = _(
					"Reserved Qty ({0}) cannot be a fraction. To allow this, disable '{1}' in UOM {3}."
				).format(
					flt(self.reserved_qty, self.precision("reserved_qty")),
					frappe.bold(_("Must be Whole Number")),
					frappe.bold(self.stock_uom),
				)
				frappe.throw(msg)

	def set_reservation_based_on(self) -> None:
		"""Sets `Reservation Based On` based on `Has Serial No` and `Has Batch No`."""

		if (self.reservation_based_on == "Serial and Batch") and (
			not self.has_serial_no and not self.has_batch_no
		):
			self.db_set("reservation_based_on", "Qty")

	def validate_reservation_based_on_qty(self) -> None:
		"""Validates `Reserved Qty` when `Reservation Based On` is `Qty`."""

		if self.reservation_based_on == "Qty":
			self.validate_with_max_reserved_qty(self.reserved_qty)

	def auto_reserve_serial_and_batch(self, based_on: str = None) -> None:
		"""Auto pick Serial and Batch Nos to reserve when `Reservation Based On` is `Serial and Batch`."""

		if (
			not self.against_pick_list
			and (self.get("_action") == "submit")
			and (self.has_serial_no or self.has_batch_no)
			and cint(frappe.db.get_single_value("Stock Settings", "auto_reserve_serial_and_batch"))
		):
			from erpnext.stock.doctype.batch.batch import get_available_batches
			from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos_for_outward
			from erpnext.stock.serial_batch_bundle import get_serial_nos_batch

			self.reservation_based_on = "Serial and Batch"
			self.sb_entries.clear()
			kwargs = frappe._dict(
				{
					"item_code": self.item_code,
					"warehouse": self.warehouse,
					"qty": abs(self.reserved_qty) or 0,
					"based_on": based_on
					or frappe.db.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"),
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
			allow_partial_reservation = frappe.db.get_single_value(
				"Stock Settings", "allow_partial_reservation"
			)

			available_serial_nos = []
			if self.has_serial_no:
				available_serial_nos = get_available_serial_nos_to_reserve(
					self.item_code, self.warehouse, self.has_batch_no, ignore_sre=self.name
				)

				if not available_serial_nos:
					msg = _("Stock not available for Item {0} in Warehouse {1}.").format(
						frappe.bold(self.item_code), frappe.bold(self.warehouse)
					)
					frappe.throw(msg)

			qty_to_be_reserved = 0
			selected_batch_nos, selected_serial_nos = [], []
			for entry in self.sb_entries:
				entry.warehouse = self.warehouse

				if self.has_serial_no:
					entry.qty = 1

					key = (
						(entry.serial_no, self.warehouse, entry.batch_no)
						if self.has_batch_no
						else (entry.serial_no, self.warehouse)
					)
					if key not in available_serial_nos:
						msg = _(
							"Row #{0}: Serial No {1} for Item {2} is not available in {3} {4} or might be reserved in another {5}."
						).format(
							entry.idx,
							frappe.bold(entry.serial_no),
							frappe.bold(self.item_code),
							_("Batch {0} and Warehouse").format(frappe.bold(entry.batch_no))
							if self.has_batch_no
							else _("Warehouse"),
							frappe.bold(self.warehouse),
							frappe.bold("Stock Reservation Entry"),
						)

						frappe.throw(msg)

					if entry.serial_no in selected_serial_nos:
						msg = _("Row #{0}: Serial No {1} is already selected.").format(
							entry.idx, frappe.bold(entry.serial_no)
						)
						frappe.throw(msg)
					else:
						selected_serial_nos.append(entry.serial_no)

				elif self.has_batch_no:
					if cint(frappe.db.get_value("Batch", entry.batch_no, "disabled")):
						msg = _(
							"Row #{0}: Stock cannot be reserved for Item {1} against a disabled Batch {2}."
						).format(
							entry.idx, frappe.bold(self.item_code), frappe.bold(entry.batch_no)
						)
						frappe.throw(msg)

					available_qty_to_reserve = get_available_qty_to_reserve(
						self.item_code, self.warehouse, entry.batch_no, ignore_sre=self.name
					)

					if available_qty_to_reserve <= 0:
						msg = _(
							"Row #{0}: Stock not availabe to reserve for Item {1} against Batch {2} in Warehouse {3}."
						).format(
							entry.idx,
							frappe.bold(self.item_code),
							frappe.bold(entry.batch_no),
							frappe.bold(self.warehouse),
						)
						frappe.throw(msg)

					if entry.qty > available_qty_to_reserve:
						if allow_partial_reservation:
							entry.qty = available_qty_to_reserve
							if self.get("_action") == "update_after_submit":
								entry.db_update()
						else:
							msg = _(
								"Row #{0}: Qty should be less than or equal to Available Qty to Reserve (Actual Qty - Reserved Qty) {1} for Iem {2} against Batch {3} in Warehouse {4}."
							).format(
								entry.idx,
								frappe.bold(available_qty_to_reserve),
								frappe.bold(self.item_code),
								frappe.bold(entry.batch_no),
								frappe.bold(self.warehouse),
							)
							frappe.throw(msg)

					if entry.batch_no in selected_batch_nos:
						msg = _("Row #{0}: Batch No {1} is already selected.").format(
							entry.idx, frappe.bold(entry.batch_no)
						)
						frappe.throw(msg)
					else:
						selected_batch_nos.append(entry.batch_no)

				qty_to_be_reserved += entry.qty

			if not qty_to_be_reserved:
				msg = _("Please select Serial/Batch Nos to reserve or change Reservation Based On to Qty.")
				frappe.throw(msg)

			# Should be called after validating Serial and Batch Nos.
			self.validate_with_max_reserved_qty(qty_to_be_reserved)
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

	def update_reserved_qty_in_pick_list(
		self, reserved_qty_field: str = "stock_reserved_qty", update_modified: bool = True
	) -> None:
		"""Updates total reserved qty in the Pick List."""

		if self.against_pick_list and self.against_pick_list_item:
			sre = frappe.qb.DocType("Stock Reservation Entry")
			reserved_qty = (
				frappe.qb.from_(sre)
				.select(Sum(sre.reserved_qty))
				.where(
					(sre.docstatus == 1)
					& (sre.against_pick_list == self.against_pick_list)
					& (sre.against_pick_list_item == self.against_pick_list_item)
				)
			).run(as_list=True)[0][0] or 0

			frappe.db.set_value(
				"Pick List Item",
				self.against_pick_list_item,
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

		if self.status in ("Partially Delivered", "Delivered"):
			msg = _(
				"{0} {1} cannot be updated. If you need to make changes, we recommend canceling the existing entry and creating a new one."
			).format(self.status, self.doctype)
			frappe.throw(msg)

		if self.against_pick_list:
			msg = _(
				"Stock Reservation Entry created against a Pick List cannot be updated. If you need to make changes, we recommend canceling the existing entry and creating a new one."
			)
			frappe.throw(msg)

		if self.delivered_qty > 0:
			msg = _("Stock Reservation Entry cannot be updated as it has been delivered.")
			frappe.throw(msg)

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
			msg = _("Item {0} is already delivered for Sales Order {1}.").format(
				frappe.bold(self.item_code), frappe.bold(self.voucher_no)
			)

			if self.docstatus == 1:
				self.cancel()
				return frappe.msgprint(msg)
			else:
				frappe.throw(msg)

		if qty_to_be_reserved > max_reserved_qty:
			msg = """
				Cannot reserve more than Max Reserved Qty {0} {1}.<br /><br />
				The <b>Max Reserved Qty</b> is calculated as follows:<br />
				<ul>
					<li><b>Available Qty To Reserve</b> = (Actual Stock Qty - Reserved Stock Qty)</li>
					<li><b>Voucher Qty</b> = Voucher Item Qty</li>
					<li><b>Delivered Qty</b> = Qty delivered against the Voucher Item</li>
					<li><b>Total Reserved Qty</b> = Qty reserved against the Voucher Item</li>
					<li><b>Max Reserved Qty</b> = Minimum of (Available Qty To Reserve, (Voucher Qty - Delivered Qty - Total Reserved Qty))</li>
				</ul>
			""".format(
				frappe.bold(max_reserved_qty), self.stock_uom
			)
			frappe.throw(msg)

		if qty_to_be_reserved <= self.delivered_qty:
			msg = _("Reserved Qty should be greater than Delivered Qty.")
			frappe.throw(msg)


def validate_stock_reservation_settings(voucher: object) -> None:
	"""Raises an exception if `Stock Reservation` is not enabled or `Voucher Type` is not allowed."""

	if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		msg = _("Please enable {0} in the {1}.").format(
			frappe.bold("Stock Reservation"), frappe.bold("Stock Settings")
		)
		frappe.throw(msg)

	# Voucher types allowed for stock reservation
	allowed_voucher_types = ["Sales Order"]

	if voucher.doctype not in allowed_voucher_types:
		msg = _("Stock Reservation can only be created against {0}.").format(
			", ".join(allowed_voucher_types)
		)
		frappe.throw(msg)


def get_available_qty_to_reserve(
	item_code: str, warehouse: str, batch_no: str = None, ignore_sre=None
) -> float:
	"""Returns `Available Qty to Reserve (Actual Qty - Reserved Qty)` for Item, Warehouse and Batch combination."""

	from erpnext.stock.doctype.batch.batch import get_batch_qty
	from erpnext.stock.utils import get_stock_balance

	if batch_no:
		return get_batch_qty(
			item_code=item_code, warehouse=warehouse, batch_no=batch_no, ignore_voucher_nos=[ignore_sre]
		)

	available_qty = get_stock_balance(item_code, warehouse)

	if available_qty:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		query = (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.reserved_qty >= sre.delivered_qty)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		)

		if ignore_sre:
			query = query.where(sre.name != ignore_sre)

		reserved_qty = query.run()[0][0] or 0.0

		if reserved_qty:
			return available_qty - reserved_qty

	return available_qty


def get_available_serial_nos_to_reserve(
	item_code: str, warehouse: str, has_batch_no: bool = False, ignore_sre=None
) -> list[tuple]:
	"""Returns Available Serial Nos to Reserve (Available Serial Nos - Reserved Serial Nos)` for Item, Warehouse and Batch combination."""

	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_available_serial_nos,
	)

	available_serial_nos = get_available_serial_nos(
		frappe._dict(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"has_batch_no": has_batch_no,
				"ignore_voucher_nos": [ignore_sre],
			}
		)
	)

	available_serial_nos_list = []
	if available_serial_nos:
		available_serial_nos_list = [tuple(d.values()) for d in available_serial_nos]

		sre = frappe.qb.DocType("Stock Reservation Entry")
		sb_entry = frappe.qb.DocType("Serial and Batch Entry")
		query = (
			frappe.qb.from_(sre)
			.left_join(sb_entry)
			.on(sre.name == sb_entry.parent)
			.select(sb_entry.serial_no, sre.warehouse)
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.reserved_qty >= sre.delivered_qty)
				& (sre.status.notin(["Delivered", "Cancelled"]))
				& (sre.reservation_based_on == "Serial and Batch")
			)
		)

		if has_batch_no:
			query = query.select(sb_entry.batch_no)

		if ignore_sre:
			query = query.where(sre.name != ignore_sre)

		reserved_serial_nos = query.run()

		if reserved_serial_nos:
			return list(set(available_serial_nos_list) - set(reserved_serial_nos))

	return available_serial_nos_list


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


def get_sre_details_for_voucher(voucher_type: str, voucher_no: str) -> list[dict]:
	"""Returns a list of SREs for the provided voucher."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	return (
		frappe.qb.from_(sre)
		.select(
			sre.name,
			sre.item_code,
			sre.warehouse,
			sre.voucher_type,
			sre.voucher_no,
			sre.voucher_detail_no,
			(sre.reserved_qty - sre.delivered_qty).as_("reserved_qty"),
			sre.has_serial_no,
			sre.has_batch_no,
			sre.reservation_based_on,
		)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.reserved_qty > sre.delivered_qty)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.orderby(sre.creation)
	).run(as_dict=True)


def get_serial_batch_entries_for_voucher(sre_name: str) -> list[dict]:
	"""Returns a list of `Serial and Batch Entries` for the provided voucher."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	sb_entry = frappe.qb.DocType("Serial and Batch Entry")

	return (
		frappe.qb.from_(sre)
		.inner_join(sb_entry)
		.on(sre.name == sb_entry.parent)
		.select(
			sb_entry.serial_no,
			sb_entry.batch_no,
			(sb_entry.qty - sb_entry.delivered_qty).as_("qty"),
		)
		.where(
			(sre.docstatus == 1) & (sre.name == sre_name) & (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.where(sb_entry.qty > sb_entry.delivered_qty)
		.orderby(sb_entry.creation)
	).run(as_dict=True)


def get_ssb_bundle_for_voucher(sre: dict) -> object | None:
	"""Returns a new `Serial and Batch Bundle` against the provided SRE."""

	sb_entries = get_serial_batch_entries_for_voucher(sre["name"])

	if sb_entries:
		bundle = frappe.new_doc("Serial and Batch Bundle")
		bundle.type_of_transaction = "Outward"
		bundle.voucher_type = "Delivery Note"

		for field in ("item_code", "warehouse", "has_serial_no", "has_batch_no"):
			setattr(bundle, field, sre[field])

		for sb_entry in sb_entries:
			bundle.append("entries", sb_entry)

		bundle.save()

		return bundle.name


def has_reserved_stock(voucher_type: str, voucher_no: str, voucher_detail_no: str = None) -> bool:
	"""Returns True if there is any Stock Reservation Entry for the given voucher."""

	if get_stock_reservation_entries_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, fields=["name"]
	):
		return True

	return False


def create_stock_reservation_entries_for_so_items(
	so: object,
	items_details: list[dict] = None,
	against_pick_list: bool = False,
	notify=True,
) -> None:
	"""Creates Stock Reservation Entries for Sales Order Items."""

	from erpnext.selling.doctype.sales_order.sales_order import get_unreserved_qty

	if not against_pick_list and (
		so.get("_action") == "submit"
		and so.set_warehouse
		and cint(frappe.get_cached_value("Warehouse", so.set_warehouse, "is_group"))
	):
		return frappe.msgprint(
			_("Stock cannot be reserved in the group warehouse {0}.").format(frappe.bold(so.set_warehouse))
		)

	validate_stock_reservation_settings(so)

	allow_partial_reservation = frappe.db.get_single_value(
		"Stock Settings", "allow_partial_reservation"
	)

	items = []
	if items_details:
		for item in items_details:
			so_item = frappe.get_doc(
				"Sales Order Item", item.get("sales_order_item") if against_pick_list else item.get("name")
			)
			so_item.reserve_stock = 1
			so_item.warehouse = item.get("warehouse")
			so_item.qty_to_reserve = (
				item.get("picked_qty") - item.get("stock_reserved_qty", 0)
				if against_pick_list
				else (flt(item.get("qty_to_reserve")) * flt(so_item.conversion_factor, 1))
			)

			if against_pick_list:
				so_item.pick_list = item.get("parent")
				so_item.pick_list_item = item.get("name")
				so_item.pick_list_sbb = item.get("serial_and_batch_bundle")

			items.append(so_item)

	sre_count = 0
	reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Sales Order", so.name)

	for item in items if items_details else so.get("items"):
		# Skip if `Reserved Stock` is not checked for the item.
		if not item.get("reserve_stock"):
			continue

		# Stock should be reserved from the Pick List if has Picked Qty.
		if not against_pick_list and flt(item.picked_qty) > 0:
			frappe.throw(
				_(
					"Row #{0}: Item {1} has been picked, please create a Stock Reservation from the Pick List."
				).format(item.idx, frappe.bold(item.item_code))
			)

		is_stock_item, has_serial_no, has_batch_no = frappe.get_cached_value(
			"Item", item.item_code, ["is_stock_item", "has_serial_no", "has_batch_no"]
		)

		# Skip if Non-Stock Item.
		if not is_stock_item:
			frappe.msgprint(
				_("Row #{0}: Stock cannot be reserved for a non-stock Item {1}").format(
					item.idx, frappe.bold(item.item_code)
				),
				title=_("Stock Reservation"),
				indicator="yellow",
			)
			item.db_set("reserve_stock", 0)
			continue

		# Skip if Group Warehouse.
		if frappe.get_cached_value("Warehouse", item.warehouse, "is_group"):
			frappe.msgprint(
				_("Row #{0}: Stock cannot be reserved in group warehouse {1}.").format(
					item.idx, frappe.bold(item.warehouse)
				),
				title=_("Stock Reservation"),
				indicator="yellow",
			)
			continue

		unreserved_qty = get_unreserved_qty(item, reserved_qty_details)

		# Stock is already reserved for the item, notify the user and skip the item.
		if unreserved_qty <= 0:
			frappe.msgprint(
				_("Row #{0}: Stock is already reserved for the Item {1}.").format(
					item.idx, frappe.bold(item.item_code)
				),
				title=_("Stock Reservation"),
				indicator="yellow",
			)
			continue

		available_qty_to_reserve = get_available_qty_to_reserve(item.item_code, item.warehouse)

		# No stock available to reserve, notify the user and skip the item.
		if available_qty_to_reserve <= 0:
			frappe.msgprint(
				_("Row #{0}: No available stock to reserve for the Item {1} in Warehouse {2}.").format(
					item.idx, frappe.bold(item.item_code), frappe.bold(item.warehouse)
				),
				title=_("Stock Reservation"),
				indicator="orange",
			)
			continue

		# The quantity which can be reserved.
		qty_to_be_reserved = min(unreserved_qty, available_qty_to_reserve)

		if hasattr(item, "qty_to_reserve"):
			if item.qty_to_reserve <= 0:
				frappe.msgprint(
					_("Row #{0}: Quantity to reserve for the Item {1} should be greater than 0.").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="orange",
				)
				continue
			else:
				qty_to_be_reserved = min(qty_to_be_reserved, item.qty_to_reserve)

		# Partial Reservation
		if qty_to_be_reserved < unreserved_qty:
			if not item.get("qty_to_reserve") or qty_to_be_reserved < flt(item.get("qty_to_reserve")):
				msg = _("Row #{0}: Only {1} available to reserve for the Item {2}").format(
					item.idx,
					frappe.bold(str(qty_to_be_reserved / item.conversion_factor) + " " + item.uom),
					frappe.bold(item.item_code),
				)
				frappe.msgprint(msg, title=_("Stock Reservation"), indicator="orange")

			# Skip the item if `Partial Reservation` is disabled in the Stock Settings.
			if not allow_partial_reservation:
				continue

		sre = frappe.new_doc("Stock Reservation Entry")

		sre.item_code = item.item_code
		sre.warehouse = item.warehouse
		sre.has_serial_no = has_serial_no
		sre.has_batch_no = has_batch_no
		sre.voucher_type = so.doctype
		sre.voucher_no = so.name
		sre.voucher_detail_no = item.name
		sre.available_qty = available_qty_to_reserve
		sre.voucher_qty = item.stock_qty
		sre.reserved_qty = qty_to_be_reserved
		sre.company = so.company
		sre.stock_uom = item.stock_uom
		sre.project = so.project

		if against_pick_list:
			sre.against_pick_list = item.pick_list
			sre.against_pick_list_item = item.pick_list_item

			if item.pick_list_sbb:
				sbb = frappe.get_doc("Serial and Batch Bundle", item.pick_list_sbb)
				sre.reservation_based_on = "Serial and Batch"
				for entry in sbb.entries:
					sre.append(
						"sb_entries",
						{
							"serial_no": entry.serial_no,
							"batch_no": entry.batch_no,
							"qty": 1 if has_serial_no else abs(entry.qty),
							"warehouse": entry.warehouse,
						},
					)

		sre.save()
		sre.submit()

		sre_count += 1

	if sre_count and notify:
		frappe.msgprint(_("Stock Reservation Entries Created"), alert=True, indicator="green")


def cancel_stock_reservation_entries(
	voucher_type: str = None,
	voucher_no: str = None,
	voucher_detail_no: str = None,
	against_pick_list: str = None,
	sre_list: list[dict] = None,
	notify: bool = True,
) -> None:
	"""Cancel Stock Reservation Entries."""

	if not sre_list and against_pick_list:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		sre_list = (
			frappe.qb.from_(sre)
			.select(sre.name)
			.where(
				(sre.docstatus == 1)
				& (sre.against_pick_list == against_pick_list)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
			.orderby(sre.creation)
		).run(as_dict=True)

	elif not sre_list and (voucher_type and voucher_no):
		sre_list = get_stock_reservation_entries_for_voucher(
			voucher_type, voucher_no, voucher_detail_no, fields=["name"]
		)

	if sre_list:
		for sre in sre_list:
			frappe.get_doc("Stock Reservation Entry", sre["name"]).cancel()

		if notify:
			msg = _("Stock Reservation Entries Cancelled")
			frappe.msgprint(msg, alert=True, indicator="red")


@frappe.whitelist()
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
