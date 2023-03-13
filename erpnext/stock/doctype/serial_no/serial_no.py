# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from typing import List, Optional, Union

import frappe
from frappe import ValidationError, _
from frappe.model.naming import make_autoname
from frappe.query_builder.functions import Coalesce
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate, now, nowdate, safe_json_loads

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.get_item_details import get_reserved_qty_for_so


class SerialNoCannotCreateDirectError(ValidationError):
	pass


class SerialNoCannotCannotChangeError(ValidationError):
	pass


class SerialNoNotRequiredError(ValidationError):
	pass


class SerialNoRequiredError(ValidationError):
	pass


class SerialNoQtyError(ValidationError):
	pass


class SerialNoItemError(ValidationError):
	pass


class SerialNoWarehouseError(ValidationError):
	pass


class SerialNoBatchError(ValidationError):
	pass


class SerialNoNotExistsError(ValidationError):
	pass


class SerialNoDuplicateError(ValidationError):
	pass


class SerialNo(StockController):
	def __init__(self, *args, **kwargs):
		super(SerialNo, self).__init__(*args, **kwargs)
		self.via_stock_ledger = False

	def validate(self):
		if self.get("__islocal") and self.warehouse and not self.via_stock_ledger:
			frappe.throw(
				_(
					"New Serial No cannot have Warehouse. Warehouse must be set by Stock Entry or Purchase Receipt"
				),
				SerialNoCannotCreateDirectError,
			)

		self.set_maintenance_status()

	def set_maintenance_status(self):
		if not self.warranty_expiry_date and not self.amc_expiry_date:
			self.maintenance_status = None

		if self.warranty_expiry_date and getdate(self.warranty_expiry_date) < getdate(nowdate()):
			self.maintenance_status = "Out of Warranty"

		if self.amc_expiry_date and getdate(self.amc_expiry_date) < getdate(nowdate()):
			self.maintenance_status = "Out of AMC"

		if self.amc_expiry_date and getdate(self.amc_expiry_date) >= getdate(nowdate()):
			self.maintenance_status = "Under AMC"

		if self.warranty_expiry_date and getdate(self.warranty_expiry_date) >= getdate(nowdate()):
			self.maintenance_status = "Under Warranty"

	def on_trash(self):
		sl_entries = frappe.db.sql(
			"""select serial_no from `tabStock Ledger Entry`
			where serial_no like %s and item_code=%s and is_cancelled=0""",
			("%%%s%%" % self.name, self.item_code),
			as_dict=True,
		)

		# Find the exact match
		sle_exists = False
		for d in sl_entries:
			if self.name.upper() in get_serial_nos(d.serial_no):
				sle_exists = True
				break

		if sle_exists:
			frappe.throw(
				_("Cannot delete Serial No {0}, as it is used in stock transactions").format(self.name)
			)


def process_serial_no(sle):
	item_det = get_item_details(sle.item_code)
	validate_serial_no(sle, item_det)


def validate_serial_no(sle, item_det):
	serial_nos = get_serial_nos(sle.serial_and_batch_bundle) if sle.serial_and_batch_bundle else []
	validate_material_transfer_entry(sle)

	if item_det.has_serial_no == 0:
		if serial_nos:
			frappe.throw(
				_("Item {0} is not setup for Serial Nos. Column must be blank").format(sle.item_code),
				SerialNoNotRequiredError,
			)
	elif not sle.is_cancelled:
		return
		if serial_nos:
			if cint(sle.actual_qty) != flt(sle.actual_qty):
				frappe.throw(
					_("Serial No {0} quantity {1} cannot be a fraction").format(sle.item_code, sle.actual_qty)
				)

			if len(serial_nos) and len(serial_nos) != abs(cint(sle.actual_qty)):
				frappe.throw(
					_("{0} Serial Numbers required for Item {1}. You have provided {2}.").format(
						abs(sle.actual_qty), sle.item_code, len(serial_nos)
					),
					SerialNoQtyError,
				)

			if len(serial_nos) != len(set(serial_nos)):
				frappe.throw(
					_("Duplicate Serial No entered for Item {0}").format(sle.item_code), SerialNoDuplicateError
				)

			for serial_no in serial_nos:
				if frappe.db.exists("Serial No", serial_no):
					sr = frappe.db.get_value(
						"Serial No",
						serial_no,
						[
							"name",
							"item_code",
							"batch_no",
							"sales_order",
							"delivery_document_no",
							"delivery_document_type",
							"warehouse",
							"purchase_document_type",
							"purchase_document_no",
							"company",
							"status",
						],
						as_dict=1,
					)

					if sr.item_code != sle.item_code:
						if not allow_serial_nos_with_different_item(serial_no, sle):
							frappe.throw(
								_("Serial No {0} does not belong to Item {1}").format(serial_no, sle.item_code),
								SerialNoItemError,
							)

					if cint(sle.actual_qty) > 0 and has_serial_no_exists(sr, sle):
						doc_name = frappe.bold(get_link_to_form(sr.purchase_document_type, sr.purchase_document_no))
						frappe.throw(
							_("Serial No {0} has already been received in the {1} #{2}").format(
								frappe.bold(serial_no), sr.purchase_document_type, doc_name
							),
							SerialNoDuplicateError,
						)

					if (
						sr.delivery_document_no
						and sle.voucher_type not in ["Stock Entry", "Stock Reconciliation"]
						and sle.voucher_type == sr.delivery_document_type
					):
						return_against = frappe.db.get_value(sle.voucher_type, sle.voucher_no, "return_against")
						if return_against and return_against != sr.delivery_document_no:
							frappe.throw(_("Serial no {0} has been already returned").format(sr.name))

					if cint(sle.actual_qty) < 0:
						if sr.warehouse != sle.warehouse:
							frappe.throw(
								_("Serial No {0} does not belong to Warehouse {1}").format(serial_no, sle.warehouse),
								SerialNoWarehouseError,
							)

						if not sr.purchase_document_no:
							frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)

						if sle.voucher_type in ("Delivery Note", "Sales Invoice"):

							if sr.batch_no and sr.batch_no != sle.batch_no:
								frappe.throw(
									_("Serial No {0} does not belong to Batch {1}").format(serial_no, sle.batch_no),
									SerialNoBatchError,
								)

							if not sle.is_cancelled and not sr.warehouse:
								frappe.throw(
									_("Serial No {0} does not belong to any Warehouse").format(serial_no),
									SerialNoWarehouseError,
								)

							# if Sales Order reference in Serial No validate the Delivery Note or Invoice is against the same
							if sr.sales_order:
								if sle.voucher_type == "Sales Invoice":
									if not frappe.db.exists(
										"Sales Invoice Item",
										{"parent": sle.voucher_no, "item_code": sle.item_code, "sales_order": sr.sales_order},
									):
										frappe.throw(
											_(
												"Cannot deliver Serial No {0} of item {1} as it is reserved to fullfill Sales Order {2}"
											).format(sr.name, sle.item_code, sr.sales_order)
										)
								elif sle.voucher_type == "Delivery Note":
									if not frappe.db.exists(
										"Delivery Note Item",
										{
											"parent": sle.voucher_no,
											"item_code": sle.item_code,
											"against_sales_order": sr.sales_order,
										},
									):
										invoice = frappe.db.get_value(
											"Delivery Note Item",
											{"parent": sle.voucher_no, "item_code": sle.item_code},
											"against_sales_invoice",
										)
										if not invoice or frappe.db.exists(
											"Sales Invoice Item",
											{"parent": invoice, "item_code": sle.item_code, "sales_order": sr.sales_order},
										):
											frappe.throw(
												_(
													"Cannot deliver Serial No {0} of item {1} as it is reserved to fullfill Sales Order {2}"
												).format(sr.name, sle.item_code, sr.sales_order)
											)
							# if Sales Order reference in Delivery Note or Invoice validate SO reservations for item
							if sle.voucher_type == "Sales Invoice":
								sales_order = frappe.db.get_value(
									"Sales Invoice Item",
									{"parent": sle.voucher_no, "item_code": sle.item_code},
									"sales_order",
								)
								if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
									validate_so_serial_no(sr, sales_order)
							elif sle.voucher_type == "Delivery Note":
								sales_order = frappe.get_value(
									"Delivery Note Item",
									{"parent": sle.voucher_no, "item_code": sle.item_code},
									"against_sales_order",
								)
								if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
									validate_so_serial_no(sr, sales_order)
								else:
									sales_invoice = frappe.get_value(
										"Delivery Note Item",
										{"parent": sle.voucher_no, "item_code": sle.item_code},
										"against_sales_invoice",
									)
									if sales_invoice:
										sales_order = frappe.db.get_value(
											"Sales Invoice Item",
											{"parent": sales_invoice, "item_code": sle.item_code},
											"sales_order",
										)
										if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
											validate_so_serial_no(sr, sales_order)
				elif cint(sle.actual_qty) < 0:
					# transfer out
					frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)
		elif cint(sle.actual_qty) < 0 or not item_det.serial_no_series:
			frappe.throw(
				_("Serial Nos Required for Serialized Item {0}").format(sle.item_code), SerialNoRequiredError
			)
	elif serial_nos:
		return
		# SLE is being cancelled and has serial nos
		for serial_no in serial_nos:
			check_serial_no_validity_on_cancel(serial_no, sle)


def check_serial_no_validity_on_cancel(serial_no, sle):
	sr = frappe.db.get_value(
		"Serial No", serial_no, ["name", "warehouse", "company", "status"], as_dict=1
	)
	sr_link = frappe.utils.get_link_to_form("Serial No", serial_no)
	doc_link = frappe.utils.get_link_to_form(sle.voucher_type, sle.voucher_no)
	actual_qty = cint(sle.actual_qty)
	is_stock_reco = sle.voucher_type == "Stock Reconciliation"
	msg = None

	if sr and (actual_qty < 0 or is_stock_reco) and (sr.warehouse and sr.warehouse != sle.warehouse):
		# receipt(inward) is being cancelled
		msg = _("Cannot cancel {0} {1} as Serial No {2} does not belong to the warehouse {3}").format(
			sle.voucher_type, doc_link, sr_link, frappe.bold(sle.warehouse)
		)
	elif sr and actual_qty > 0 and not is_stock_reco:
		# delivery is being cancelled, check for warehouse.
		if sr.warehouse:
			# serial no is active in another warehouse/company.
			msg = _("Cannot cancel {0} {1} as Serial No {2} is active in warehouse {3}").format(
				sle.voucher_type, doc_link, sr_link, frappe.bold(sr.warehouse)
			)
		elif sr.company != sle.company and sr.status == "Delivered":
			# serial no is inactive (allowed) or delivered from another company (block).
			msg = _("Cannot cancel {0} {1} as Serial No {2} does not belong to the company {3}").format(
				sle.voucher_type, doc_link, sr_link, frappe.bold(sle.company)
			)

	if msg:
		frappe.throw(msg, title=_("Cannot cancel"))


def validate_material_transfer_entry(sle_doc):
	sle_doc.update({"skip_update_serial_no": False, "skip_serial_no_validaiton": False})

	if (
		sle_doc.voucher_type == "Stock Entry"
		and not sle_doc.is_cancelled
		and frappe.get_cached_value("Stock Entry", sle_doc.voucher_no, "purpose") == "Material Transfer"
	):
		if sle_doc.actual_qty < 0:
			sle_doc.skip_update_serial_no = True
		else:
			sle_doc.skip_serial_no_validaiton = True


def validate_so_serial_no(sr, sales_order):
	if not sr.sales_order or sr.sales_order != sales_order:
		msg = _(
			"Sales Order {0} has reservation for the item {1}, you can only deliver reserved {1} against {0}."
		).format(sales_order, sr.item_code)

		frappe.throw(_("""{0} Serial No {1} cannot be delivered""").format(msg, sr.name))


def has_serial_no_exists(sn, sle):
	if (
		sn.warehouse and not sle.skip_serial_no_validaiton and sle.voucher_type != "Stock Reconciliation"
	):
		return True

	if sn.company != sle.company:
		return False


def allow_serial_nos_with_different_item(sle_serial_no, sle):
	"""
	Allows same serial nos for raw materials and finished goods
	in Manufacture / Repack type Stock Entry
	"""
	allow_serial_nos = False
	if sle.voucher_type == "Stock Entry" and cint(sle.actual_qty) > 0:
		stock_entry = frappe.get_cached_doc("Stock Entry", sle.voucher_no)
		if stock_entry.purpose in ("Repack", "Manufacture"):
			for d in stock_entry.get("items"):
				if d.serial_no and (d.s_warehouse if not sle.is_cancelled else d.t_warehouse):
					serial_nos = get_serial_nos(d.serial_no)
					if sle_serial_no in serial_nos:
						allow_serial_nos = True

	return allow_serial_nos


def update_warehouse_in_serial_no(sle, item_det):
	serial_nos = get_serial_nos(sle.serial_and_batch_bundle)
	serial_no_data = get_serial_nos_warehouse(sle.item_code, serial_nos)

	if not serial_no_data:
		for serial_no in serial_nos:
			frappe.db.set_value("Serial No", serial_no, "warehouse", None)

	else:
		for row in serial_no_data:
			if not row.serial_no:
				continue

			warehouse = row.warehouse if row.actual_qty > 0 else None
			frappe.db.set_value("Serial No", row.serial_no, "warehouse", warehouse)


def get_serial_nos_warehouse(item_code, serial_nos):
	ledger_table = frappe.qb.DocType("Serial and Batch Ledger")
	sle_table = frappe.qb.DocType("Stock Ledger Entry")

	return (
		frappe.qb.from_(ledger_table)
		.inner_join(sle_table)
		.on(ledger_table.parent == sle_table.serial_and_batch_bundle)
		.select(
			ledger_table.serial_no,
			sle_table.actual_qty,
			ledger_table.warehouse,
		)
		.where(
			(ledger_table.serial_no.isin(serial_nos))
			& (sle_table.is_cancelled == 0)
			& (sle_table.item_code == item_code)
			& (sle_table.serial_and_batch_bundle.isnotnull())
		)
		.orderby(sle_table.posting_date, order=frappe.qb.desc)
		.orderby(sle_table.posting_time, order=frappe.qb.desc)
		.orderby(sle_table.creation, order=frappe.qb.desc)
		.groupby(ledger_table.serial_no)
	).run(as_dict=True)


def create_batch_for_serial_no(sle):
	from erpnext.stock.doctype.batch.batch import make_batch

	return make_batch(
		frappe._dict(
			{
				"item": sle.item_code,
				"reference_doctype": sle.voucher_type,
				"reference_name": sle.voucher_no,
			}
		)
	)


def auto_create_serial_nos(sle, item_details) -> List[str]:
	sr_nos = []
	serial_nos_details = []
	current_series = frappe.db.sql(
		"select current from `tabSeries` where name = %s", item_details.serial_no_series
	)

	for i in range(cint(sle.actual_qty)):
		serial_no = make_autoname(item_details.serial_no_series, "Serial No")
		sr_nos.append(serial_no)
		serial_nos_details.append(
			(
				serial_no,
				serial_no,
				now(),
				now(),
				frappe.session.user,
				frappe.session.user,
				sle.warehouse,
				sle.company,
				sle.item_code,
				item_details.item_name,
				item_details.description,
			)
		)

	if serial_nos_details:
		fields = [
			"name",
			"serial_no",
			"creation",
			"modified",
			"owner",
			"modified_by",
			"warehouse",
			"company",
			"item_code",
			"item_name",
			"description",
		]

		frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	return sr_nos


def get_auto_serial_nos(serial_no_series, qty):
	serial_nos = []
	for i in range(cint(qty)):
		serial_nos.append(get_new_serial_number(serial_no_series))

	return "\n".join(serial_nos)


def get_new_serial_number(series):
	sr_no = make_autoname(series, "Serial No")
	if frappe.db.exists("Serial No", sr_no):
		sr_no = get_new_serial_number(series)
	return sr_no


def get_items_html(serial_nos, item_code):
	body = ", ".join(serial_nos)
	return """<details><summary>
		<b>{0}:</b> {1} Serial Numbers <span class="caret"></span>
	</summary>
	<div class="small">{2}</div></details>
	""".format(
		item_code, len(serial_nos), body
	)


def get_item_details(item_code):
	return frappe.db.sql(
		"""select name, has_batch_no, docstatus,
		is_stock_item, has_serial_no, serial_no_series, description, item_name,
		item_group, stock_uom
		from tabItem where name=%s""",
		item_code,
		as_dict=True,
	)[0]


def get_serial_nos(serial_no):
	if isinstance(serial_no, list):
		return serial_no

	return [
		s.strip() for s in cstr(serial_no).strip().upper().replace(",", "\n").split("\n") if s.strip()
	]


def clean_serial_no_string(serial_no: str) -> str:
	if not serial_no:
		return ""

	serial_no_list = get_serial_nos(serial_no)
	return "\n".join(serial_no_list)


def update_serial_nos_after_submit(controller, parentfield):
	return
	stock_ledger_entries = frappe.db.sql(
		"""select voucher_detail_no, serial_no, actual_qty, warehouse
		from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s""",
		(controller.doctype, controller.name),
		as_dict=True,
	)

	if not stock_ledger_entries:
		return

	for d in controller.get(parentfield):
		if d.serial_no:
			continue

		update_rejected_serial_nos = (
			True
			if (
				controller.doctype in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt")
				and d.rejected_qty
			)
			else False
		)
		accepted_serial_nos_updated = False

		if controller.doctype == "Stock Entry":
			warehouse = d.t_warehouse
			qty = d.transfer_qty
		elif controller.doctype in ("Sales Invoice", "Delivery Note"):
			warehouse = d.warehouse
			qty = d.stock_qty
		else:
			warehouse = d.warehouse
			qty = (
				d.qty
				if controller.doctype in ["Stock Reconciliation", "Subcontracting Receipt"]
				else d.stock_qty
			)
		for sle in stock_ledger_entries:
			if sle.voucher_detail_no == d.name:
				if (
					not accepted_serial_nos_updated
					and qty
					and abs(sle.actual_qty) == abs(qty)
					and sle.warehouse == warehouse
					and sle.serial_no != d.serial_no
				):
					d.serial_no = sle.serial_no
					frappe.db.set_value(d.doctype, d.name, "serial_no", sle.serial_no)
					accepted_serial_nos_updated = True
					if not update_rejected_serial_nos:
						break
				elif (
					update_rejected_serial_nos
					and abs(sle.actual_qty) == d.rejected_qty
					and sle.warehouse == d.rejected_warehouse
					and sle.serial_no != d.rejected_serial_no
				):
					d.rejected_serial_no = sle.serial_no
					frappe.db.set_value(d.doctype, d.name, "rejected_serial_no", sle.serial_no)
					update_rejected_serial_nos = False
					if accepted_serial_nos_updated:
						break


def update_maintenance_status():
	serial_nos = frappe.db.sql(
		"""select name from `tabSerial No` where (amc_expiry_date<%s or
		warranty_expiry_date<%s) and maintenance_status not in ('Out of Warranty', 'Out of AMC')""",
		(nowdate(), nowdate()),
	)
	for serial_no in serial_nos:
		doc = frappe.get_doc("Serial No", serial_no[0])
		doc.set_maintenance_status()
		frappe.db.set_value("Serial No", doc.name, "maintenance_status", doc.maintenance_status)


def get_delivery_note_serial_no(item_code, qty, delivery_note):
	serial_nos = ""
	dn_serial_nos = frappe.db.sql_list(
		""" select name from `tabSerial No`
		where item_code = %(item_code)s and delivery_document_no = %(delivery_note)s
		and sales_invoice is null limit {0}""".format(
			cint(qty)
		),
		{"item_code": item_code, "delivery_note": delivery_note},
	)

	if dn_serial_nos and len(dn_serial_nos) > 0:
		serial_nos = "\n".join(dn_serial_nos)

	return serial_nos


@frappe.whitelist()
def auto_fetch_serial_number(
	qty: int,
	item_code: str,
	warehouse: str,
	posting_date: Optional[str] = None,
	batch_nos: Optional[Union[str, List[str]]] = None,
	for_doctype: Optional[str] = None,
	exclude_sr_nos=None,
) -> List[str]:

	filters = frappe._dict({"item_code": item_code, "warehouse": warehouse})

	if exclude_sr_nos is None:
		exclude_sr_nos = []
	else:
		exclude_sr_nos = safe_json_loads(exclude_sr_nos)
		exclude_sr_nos = get_serial_nos(clean_serial_no_string("\n".join(exclude_sr_nos)))

	if batch_nos:
		batch_nos_list = safe_json_loads(batch_nos)
		if isinstance(batch_nos_list, list):
			filters.batch_no = batch_nos_list
		else:
			filters.batch_no = [batch_nos]

	if posting_date:
		filters.expiry_date = posting_date

	serial_numbers = []
	if for_doctype == "POS Invoice":
		exclude_sr_nos.extend(get_pos_reserved_serial_nos(filters))

	serial_numbers = fetch_serial_numbers(filters, qty, do_not_include=exclude_sr_nos)

	return sorted([d.get("name") for d in serial_numbers])


def get_delivered_serial_nos(serial_nos):
	"""
	Returns serial numbers that delivered from the list of serial numbers
	"""
	from frappe.query_builder.functions import Coalesce

	SerialNo = frappe.qb.DocType("Serial No")
	serial_nos = get_serial_nos(serial_nos)
	query = (
		frappe.qb.select(SerialNo.name)
		.from_(SerialNo)
		.where((SerialNo.name.isin(serial_nos)) & (Coalesce(SerialNo.delivery_document_type, "") != ""))
	)

	result = query.run()
	if result and len(result) > 0:
		delivered_serial_nos = [row[0] for row in result]
		return delivered_serial_nos


@frappe.whitelist()
def get_pos_reserved_serial_nos(filters):
	if isinstance(filters, str):
		filters = json.loads(filters)

	POSInvoice = frappe.qb.DocType("POS Invoice")
	POSInvoiceItem = frappe.qb.DocType("POS Invoice Item")
	query = (
		frappe.qb.from_(POSInvoice)
		.from_(POSInvoiceItem)
		.select(POSInvoice.is_return, POSInvoiceItem.serial_no)
		.where(
			(POSInvoice.name == POSInvoiceItem.parent)
			& (POSInvoice.docstatus == 1)
			& (POSInvoiceItem.docstatus == 1)
			& (POSInvoiceItem.item_code == filters.get("item_code"))
			& (POSInvoiceItem.warehouse == filters.get("warehouse"))
			& (POSInvoiceItem.serial_no.isnotnull())
			& (POSInvoiceItem.serial_no != "")
		)
	)

	pos_transacted_sr_nos = query.run(as_dict=True)

	reserved_sr_nos = set()
	returned_sr_nos = set()
	for d in pos_transacted_sr_nos:
		if d.is_return == 0:
			[reserved_sr_nos.add(x) for x in get_serial_nos(d.serial_no)]
		elif d.is_return == 1:
			[returned_sr_nos.add(x) for x in get_serial_nos(d.serial_no)]

	reserved_sr_nos = list(reserved_sr_nos - returned_sr_nos)

	return reserved_sr_nos


def fetch_serial_numbers(filters, qty, do_not_include=None):
	if do_not_include is None:
		do_not_include = []

	batch_nos = filters.get("batch_no")
	expiry_date = filters.get("expiry_date")
	serial_no = frappe.qb.DocType("Serial No")

	query = (
		frappe.qb.from_(serial_no)
		.select(serial_no.name)
		.where(
			(serial_no.item_code == filters["item_code"])
			& (serial_no.warehouse == filters["warehouse"])
			& (Coalesce(serial_no.sales_invoice, "") == "")
			& (Coalesce(serial_no.delivery_document_no, "") == "")
		)
		.orderby(serial_no.creation)
		.limit(qty or 1)
	)

	if do_not_include:
		query = query.where(serial_no.name.notin(do_not_include))

	if batch_nos:
		query = query.where(serial_no.batch_no.isin(batch_nos))

	if expiry_date:
		batch = frappe.qb.DocType("Batch")
		query = (
			query.left_join(batch)
			.on(serial_no.batch_no == batch.name)
			.where(Coalesce(batch.expiry_date, "4000-12-31") >= expiry_date)
		)

	serial_numbers = query.run(as_dict=True)
	return serial_numbers
