# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from typing import List, Optional, Union

import frappe
from frappe import ValidationError, _
from frappe.model.naming import make_autoname
from frappe.query_builder.functions import Coalesce
from frappe.utils import cint, cstr, getdate, nowdate, safe_json_loads

from erpnext.controllers.stock_controller import StockController


class SerialNoCannotCreateDirectError(ValidationError):
	pass


class SerialNoCannotCannotChangeError(ValidationError):
	pass


class SerialNoWarehouseError(ValidationError):
	pass


class SerialNo(StockController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amc_expiry_date: DF.Date | None
		asset: DF.Link | None
		asset_status: DF.Literal["", "Issue", "Receipt", "Transfer"]
		batch_no: DF.Link | None
		brand: DF.Link | None
		company: DF.Link
		delivery_document_type: DF.Link | None
		description: DF.Text | None
		employee: DF.Link | None
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		location: DF.Link | None
		maintenance_status: DF.Literal[
			"", "Under Warranty", "Out of Warranty", "Under AMC", "Out of AMC"
		]
		purchase_rate: DF.Float
		serial_no: DF.Data
		status: DF.Literal["", "Active", "Inactive", "Delivered", "Expired"]
		warehouse: DF.Link | None
		warranty_expiry_date: DF.Date | None
		warranty_period: DF.Int
		work_order: DF.Link | None
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super(SerialNo, self).__init__(*args, **kwargs)
		self.via_stock_ledger = False

	def autoname(self):
		self.name = self.serial_no

		if frappe.db.get_single_value("Stock Settings", "allow_duplicate_serial_nos"):
			self.validate_duplicate_in_same_item()
			self.name = self.autoname_duplicate_serial_no()

	def autoname_duplicate_serial_no(self):
		"""
		If duplicate serial no already exists in another item
		and this behaviour is permitted, append a number to the name to maintain uniqueness.
		If not, return the name as is.
		"""
		duplicate_count_in_other_items = frappe.db.count(
			"Serial No", {"serial_no": self.serial_no, "item_code": ("!=", self.item_code)}
		)
		if duplicate_count_in_other_items > 0:
			return f"{self.serial_no}-{duplicate_count_in_other_items}"
		else:
			return self.name

	def validate_duplicate_in_same_item(self):
		"""Check to make sure duplicates are not allowed in the same item."""
		if frappe.db.exists("Serial No", {"serial_no": self.serial_no, "item_code": self.item_code}):
			frappe.throw(
				msg=_("Serial No {0} already exists for Item {1}").format(
					frappe.bold(self.serial_no), frappe.bold(self.item_code)
				),
				title=_("Duplicate"),
			)

	def validate(self):
		if self.get("__islocal") and self.warehouse and not self.via_stock_ledger:
			frappe.throw(
				_(
					"New Serial No cannot have Warehouse. Warehouse must be set by Stock Entry or Purchase Receipt"
				),
				SerialNoCannotCreateDirectError,
			)

		self.set_maintenance_status()
		self.validate_warehouse()

	def validate_warehouse(self):
		if not self.get("__islocal"):
			item_code, warehouse = frappe.db.get_value("Serial No", self.name, ["item_code", "warehouse"])
			if not self.via_stock_ledger and item_code != self.item_code:
				frappe.throw(_("Item Code cannot be changed for Serial No."), SerialNoCannotCannotChangeError)
			if not self.via_stock_ledger and warehouse != self.warehouse:
				frappe.throw(_("Warehouse cannot be changed for Serial No."), SerialNoCannotCannotChangeError)

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
			if self.name.upper() in get_serial_nos(d.serial_no, self.item_code):
				sle_exists = True
				break

		if sle_exists:
			frappe.throw(
				_("Cannot delete Serial No {0}, as it is used in stock transactions").format(self.name)
			)


def get_available_serial_nos(serial_no_series, qty, item_code) -> List[str]:
	serial_nos = []
	for i in range(cint(qty)):
		serial_nos.append(get_new_serial_number(serial_no_series, item_code))

	return serial_nos


def get_new_serial_number(series, item_code):
	sr_no = make_autoname(series, "Serial No")
	filters = {"name": sr_no}

	if frappe.db.get_single_value("Stock Settings", "allow_duplicate_serial_nos"):
		# if duplicate serial nos are allowed, check duplicacy within same item
		filters["item_code"] = item_code

	if frappe.db.exists("Serial No", filters):
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


def get_serial_nos(serial_no, item_code):
	def _get_serial_no_name(serial_no):
		"""Serial No field can be the same across different items."""
		return frappe.db.get_value("Serial No", {"serial_no": serial_no, "item_code": item_code}, "name")

	if isinstance(serial_no, list):
		return serial_no

	split_serial_nos = cstr(serial_no).strip().upper().replace(",", "\n").split("\n")
	return [_get_serial_no_name(s.strip()) for s in split_serial_nos if s.strip()]


def clean_serial_no_string(serial_no: str, item_code: str) -> str:
	if not serial_no:
		return ""

	serial_no_list = get_serial_nos(serial_no, item_code)
	return "\n".join(serial_no_list)


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
	"""NOTE: Unused but kept for backward compatibility."""

	filters = frappe._dict({"item_code": item_code, "warehouse": warehouse})

	if exclude_sr_nos is None:
		exclude_sr_nos = []
	else:
		exclude_sr_nos = safe_json_loads(exclude_sr_nos)
		exclude_sr_nos = get_serial_nos(clean_serial_no_string("\n".join(exclude_sr_nos), item_code))

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
	NOTE: Unused but kept for backward compatibility.
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
			[reserved_sr_nos.add(x) for x in get_serial_nos(d.serial_no, filters.get("item_code"))]
		elif d.is_return == 1:
			[returned_sr_nos.add(x) for x in get_serial_nos(d.serial_no, filters.get("item_code"))]

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


def get_serial_nos_for_outward(kwargs):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_available_serial_nos,
	)

	serial_nos = get_available_serial_nos(kwargs)

	if not serial_nos:
		return []

	return [d.serial_no for d in serial_nos]
