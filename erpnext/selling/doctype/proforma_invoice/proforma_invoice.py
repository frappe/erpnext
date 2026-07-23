# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, now
from frappe.utils.file_manager import save_file


class ProformaInvoice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.selling.doctype.proforma_invoice_item.proforma_invoice_item import ProformaInvoiceItem

		amended_from: DF.Link | None
		based_on: DF.Literal["Quantity", "Amount"]
		company: DF.Link
		currency: DF.Link | None
		customer: DF.Link | None
		customer_name: DF.Data | None
		emailed_to: DF.SmallText | None
		grand_total: DF.Currency
		hide_item_qty: DF.Check
		items: DF.Table[ProformaInvoiceItem]
		letter_head: DF.Link | None
		naming_series: DF.Literal["PRO-.YYYY.-"]
		print_format: DF.Link | None
		proforma_date: DF.Date
		proforma_pdf: DF.Attach | None
		sales_order: DF.Link
		sent_on: DF.Datetime | None
		status: DF.Literal["Draft", "Issued", "Cancelled"]
		total_qty: DF.Float
	# end: auto-generated types

	def validate(self) -> None:
		validate_feature_enabled()
		self.set_total_qty()

	def before_submit(self) -> None:
		self.status = "Issued"

	def on_submit(self) -> None:
		self.generate_and_attach_pdf()

	def on_cancel(self) -> None:
		self.db_set("status", "Cancelled")

	def set_total_qty(self) -> None:
		self.total_qty = sum(flt(item.qty) for item in self.items)

	def generate_and_attach_pdf(self) -> None:
		if self.proforma_pdf:
			return
		printed = self.render_pdf()
		file = save_file(printed["fname"], printed["fcontent"], self.doctype, self.name, is_private=1)
		self.db_set("proforma_pdf", file.file_url)

	def render_pdf(self) -> dict:
		"""Render the proforma PDF from an in-memory, adjusted copy of the Sales Order.

		The Sales Order copy is never saved; it exists only to reuse the standard tax/total
		calculation and print format so the proforma shows the accurate gross. Each line's qty
		and rate are set from the proforma (amount-based lines carry a derived rate), so the
		recomputed amount matches whichever basis the proforma was created on.
		"""
		sales_order = frappe.get_doc("Sales Order", self.sales_order)
		lines = {item.so_detail: item for item in self.items}
		sales_order.items = [item for item in sales_order.items if item.name in lines]
		for item in sales_order.items:
			item.qty = lines[item.name].qty
			item.rate = lines[item.name].rate
			item.discount_amount = 0
			item.discount_percentage = 0
		sales_order.run_method("calculate_taxes_and_totals")
		sales_order.proforma_no = self.name
		sales_order.proforma_date = self.proforma_date
		sales_order.hide_item_qty = self.hide_item_qty
		self.db_set("grand_total", sales_order.grand_total)
		return frappe.attach_print(
			"Sales Order",
			sales_order.name,
			doc=sales_order,
			file_name=self.name,
			print_format=self.print_format,
			letterhead=self.letter_head,
		)


@frappe.whitelist()
def get_sales_order_items(sales_order: str) -> list[dict]:
	"""Sales Order lines (with already-proformed totals) to drive the create-proforma dialog."""
	sales_order_doc = frappe.get_doc("Sales Order", sales_order)
	proformed = get_proformed_totals(sales_order)
	return [
		{
			"item_code": item.item_code,
			"item_name": item.item_name,
			"uom": item.uom,
			"so_detail": item.name,
			"qty": flt(item.qty),
			"rate": flt(item.rate),
			"amount": flt(item.amount),
			"proformed_qty": flt(proformed.get(item.name, {}).get("qty")),
			"proformed_amount": flt(proformed.get(item.name, {}).get("amount")),
		}
		for item in sales_order_doc.items
	]


def get_proformed_totals(sales_order: str) -> dict[str, dict]:
	"""Sum of issued (docstatus = 1) proforma qty and amount per Sales Order Item row."""
	proformas = frappe.get_all(
		"Proforma Invoice", filters={"sales_order": sales_order, "docstatus": 1}, pluck="name"
	)
	if not proformas:
		return {}
	item = frappe.qb.DocType("Proforma Invoice Item")
	rows = (
		frappe.qb.from_(item)
		.select(item.so_detail, Sum(item.qty).as_("qty"), Sum(item.amount).as_("amount"))
		.where(item.parent.isin(proformas))
		.groupby(item.so_detail)
	).run(as_dict=True)
	return {row.so_detail: {"qty": flt(row.qty), "amount": flt(row.amount)} for row in rows}


@frappe.whitelist()
def make_proforma_invoice(
	sales_order: str,
	items: str,
	based_on: str = "Quantity",
	hide_item_qty: bool | int = 0,
	naming_series: str | None = None,
	print_format: str | None = None,
	letter_head: str | None = None,
) -> str:
	"""The sole creation path for a Proforma Invoice (the doctype is `in_create`).

	`based_on` decides what the user edited per line: "Quantity" (rate fixed, amount = qty x rate)
	or "Amount" (both qty and amount entered, rate derived). `hide_item_qty` (Amount basis only)
	hides the qty and rate on the printed proforma for a clean value-based document.
	"""
	validate_feature_enabled()
	selected = frappe.parse_json(items)
	sales_order_doc = frappe.get_doc("Sales Order", sales_order)
	if sales_order_doc.docstatus != 1:
		frappe.throw(_("A Proforma Invoice can only be created against a submitted Sales Order."))
	so_items = {item.name: item for item in sales_order_doc.items}

	proforma = frappe.new_doc("Proforma Invoice")
	proforma.sales_order = sales_order
	proforma.based_on = based_on
	proforma.hide_item_qty = 1 if (based_on == "Amount" and int(hide_item_qty or 0)) else 0
	if naming_series:
		proforma.naming_series = naming_series
	proforma.print_format = print_format or frappe.db.get_single_value(
		"Selling Settings", "default_proforma_print_format"
	)
	proforma.letter_head = letter_head

	for row in selected:
		so_item = so_items.get(row.get("so_detail"))
		if not so_item:
			continue
		line = _proforma_line(so_item, based_on, row)
		if line:
			proforma.append("items", line)

	if not proforma.items:
		frappe.throw(_("Please enter a quantity or amount for at least one item."))

	proforma.insert()
	proforma.submit()
	return proforma.name


def _proforma_line(so_item, based_on: str, row: dict) -> dict | None:
	if based_on == "Amount":
		# Amount basis: both qty and amount are user-entered; the rate is derived.
		qty = flt(row.get("qty"))
		amount = flt(row.get("amount"))
		if amount <= 0 or qty <= 0:
			return None
		rate = amount / qty
	else:
		qty = flt(row.get("qty"))
		if qty <= 0:
			return None
		rate = flt(so_item.rate)
		amount = qty * rate

	return {
		"item_code": so_item.item_code,
		"item_name": so_item.item_name,
		"uom": so_item.uom,
		"qty": qty,
		"rate": rate,
		"amount": amount,
		"so_detail": so_item.name,
	}


@frappe.whitelist()
def send_proforma_email(proforma_name: str, recipients: str) -> None:
	proforma = frappe.get_doc("Proforma Invoice", proforma_name)
	if proforma.docstatus != 1:
		frappe.throw(_("Only an issued Proforma Invoice can be emailed."))
	if not proforma.proforma_pdf:
		frappe.throw(_("This Proforma Invoice has no PDF to send."))

	file_name = frappe.db.get_value("File", {"file_url": proforma.proforma_pdf}, "name")
	if not file_name:
		frappe.throw(_("The attached PDF file could not be found."))
	frappe.sendmail(
		recipients=[email.strip() for email in recipients.split(",") if email.strip()],
		subject=_("Proforma Invoice {0}").format(proforma.name),
		message=_("Please find attached the proforma invoice {0}.").format(proforma.name),
		attachments=[{"fid": file_name}],
	)
	proforma.db_set("sent_on", now())
	proforma.db_set("emailed_to", recipients)


def validate_feature_enabled() -> None:
	if not frappe.db.get_single_value("Selling Settings", "enable_proforma_invoice"):
		frappe.throw(_("Proforma Invoice is not enabled in Selling Settings."))
