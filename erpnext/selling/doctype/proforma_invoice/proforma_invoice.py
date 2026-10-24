# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt, now
from frappe.utils.file_manager import save_file

from erpnext.utilities.email_template import get_email_subject_and_message


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
		self.validate_amended_doc()
		self.validate_sales_order()
		self.set_item_values()
		self.set_total_qty()
		self.clear_generated_values()

	def validate_sales_order(self) -> None:
		if frappe.db.get_value("Sales Order", self.sales_order, "docstatus") != 1:
			frappe.throw(_("A Proforma Invoice can only be created against a submitted Sales Order."))

	def set_item_values(self) -> None:
		"""Copy each line's item details from its Sales Order line, then set the rate and amount."""
		so_items = {
			row.name: row
			for row in frappe.get_all(
				"Sales Order Item",
				filters={"parent": self.sales_order, "parenttype": "Sales Order"},
				fields=["name", "item_code", "item_name", "description", "uom", "rate"],
			)
		}
		for item in self.items:
			so_item = so_items.get(item.so_detail)
			if not so_item:
				frappe.throw(
					_("Row #{0}: The line does not belong to Sales Order {1}").format(
						item.idx, frappe.bold(self.sales_order)
					)
				)
			item.item_code = so_item.item_code
			item.item_name = so_item.item_name
			item.uom = so_item.uom
			item.description = item.description or so_item.description
			self.set_rate_and_amount(item, so_item.rate)

	def set_rate_and_amount(self, item, sales_order_rate: float) -> None:
		"""Quantity basis bills at the Sales Order rate; Amount basis derives the rate from the amount."""
		if flt(item.qty) <= 0:
			frappe.throw(_("Row #{0}: Qty must be a positive number").format(item.idx))
		if self.based_on == "Amount":
			if flt(item.amount) <= 0:
				frappe.throw(_("Row #{0}: Amount must be a positive number").format(item.idx))
			item.rate = flt(item.amount) / flt(item.qty)
		else:
			item.rate = sales_order_rate
			item.amount = flt(item.qty) * flt(sales_order_rate)

	def validate_amended_doc(self) -> None:
		if self.amended_from:
			frappe.throw(
				_("Cannot amend {0} {1}, please create a new one instead.").format(
					self.doctype, frappe.bold(self.amended_from)
				)
			)

	def before_submit(self) -> None:
		self.status = "Issued"

	def on_submit(self) -> None:
		self.generate_and_attach_pdf()

	def on_cancel(self) -> None:
		self.db_set("status", "Cancelled")

	def set_total_qty(self) -> None:
		self.total_qty = sum(flt(item.qty) for item in self.items)

	def clear_generated_values(self) -> None:
		"""The PDF and grand total are set on submit; never keep values sent by the client."""
		self.proforma_pdf = None
		self.grand_total = 0

	def generate_and_attach_pdf(self) -> None:
		printed = self.render_pdf()
		file = save_file(printed["fname"], printed["fcontent"], self.doctype, self.name, is_private=1)
		self.db_set("proforma_pdf", file.file_url)

	def render_pdf(self) -> dict:
		"""Render the proforma PDF from an in-memory, adjusted copy of the Sales Order."""
		sales_order = self.get_sales_order_copy()
		self.db_set("grand_total", sales_order.grand_total)
		return frappe.attach_print(
			"Sales Order",
			sales_order.name,
			doc=sales_order,
			file_name=self.name,
			print_format=self.print_format,
			letterhead=self.letter_head,
		)

	def get_sales_order_copy(self) -> Document:
		"""A Sales Order copy with only the proformed lines, reusing the standard tax/total calculation.

		The copy is never saved. Each line's qty and rate are set from the proforma, and the
		order-level fixed discount and Actual charges are scaled to the proformed share.
		"""
		sales_order = frappe.get_doc("Sales Order", self.sales_order)
		lines = {item.so_detail: item for item in self.items}
		prorate_fixed_charges(sales_order, self.get_order_share(sales_order))
		sales_order.items = [item for item in sales_order.items if item.name in lines]
		for item in sales_order.items:
			item.qty = lines[item.name].qty
			item.rate = lines[item.name].rate
			item.description = lines[item.name].description
			item.discount_amount = 0
			item.discount_percentage = 0
		sales_order.run_method("calculate_taxes_and_totals")
		if flt(sales_order.grand_total) < 0:
			frappe.throw(_("The grand total of a Proforma Invoice cannot be negative."))
		sales_order.proforma_no = self.name
		sales_order.proforma_date = self.proforma_date
		sales_order.hide_item_qty = self.hide_item_qty
		return sales_order

	def get_order_share(self, sales_order: Document) -> float:
		"""Share of the Sales Order total that this proforma covers."""
		if not flt(sales_order.total):
			return 1
		return sum(flt(item.amount) for item in self.items) / flt(sales_order.total)

	def get_email_content(self) -> tuple[str, str]:
		return get_email_subject_and_message(
			frappe.db.get_single_value("Selling Settings", "proforma_email_template"),
			{"doc": self},
			default_subject=_("Proforma Invoice {0}").format(self.name),
			default_message=_("Please find attached the proforma invoice {0}.").format(self.name),
		)


@frappe.whitelist()
def get_sales_order_items(sales_order: str) -> list[dict]:
	"""Sales Order lines (with already-proformed totals) to drive the create-proforma dialog."""
	# this returns line rates and amounts for a caller-named order, so the order itself is what
	# decides access. check_permission applies User Permissions, which a doctype check would not.
	sales_order_doc = frappe.get_doc("Sales Order", sales_order, check_permission="read")
	proformed = get_proformed_totals(sales_order)
	return [
		{
			"item_code": item.item_code,
			"item_name": item.item_name,
			"description": item.description,
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
	"""Create and submit a Proforma Invoice from the Sales Order dialog.

	`based_on` decides what the user edited per line: "Quantity" (rate fixed, amount = qty x rate)
	or "Amount" (both qty and amount entered, rate derived). `hide_item_qty` (Amount basis only)
	hides the qty and rate on the printed proforma for a clean value-based document.
	"""
	validate_feature_enabled()
	proforma = frappe.new_doc("Proforma Invoice")
	proforma.sales_order = sales_order
	proforma.based_on = based_on
	proforma.hide_item_qty = 1 if (based_on == "Amount" and int(hide_item_qty or 0)) else 0
	if naming_series:
		proforma.naming_series = naming_series
	proforma.print_format = (
		print_format
		or frappe.db.get_single_value("Selling Settings", "default_proforma_print_format")
		or "Proforma Invoice"
	)
	proforma.letter_head = letter_head

	for row in frappe.parse_json(items):
		proforma.append(
			"items",
			{
				"so_detail": row.get("so_detail"),
				"qty": row.get("qty"),
				"amount": row.get("amount"),
				"description": row.get("description"),
			},
		)

	if not proforma.items:
		frappe.throw(_("Please enter a quantity or amount for at least one item."))

	proforma.insert()
	proforma.submit()
	return proforma.name


@frappe.whitelist()
def send_proforma_email(proforma_name: str, recipients: str) -> None:
	proforma = frappe.get_doc("Proforma Invoice", proforma_name)
	proforma.check_permission("email")
	if proforma.docstatus != 1:
		frappe.throw(_("Only an issued Proforma Invoice can be emailed."))
	if not proforma.proforma_pdf:
		frappe.throw(_("This Proforma Invoice has no PDF to send."))

	file_name = frappe.db.get_value(
		"File",
		{
			"file_url": proforma.proforma_pdf,
			"attached_to_doctype": proforma.doctype,
			"attached_to_name": proforma.name,
		},
		"name",
	)
	if not file_name:
		frappe.throw(_("The attached PDF file could not be found."))
	subject, message = proforma.get_email_content()
	frappe.sendmail(
		recipients=[email.strip() for email in recipients.split(",") if email.strip()],
		subject=subject,
		message=message,
		attachments=[{"fid": file_name}],
	)
	proforma.db_set("sent_on", now())
	proforma.db_set("emailed_to", recipients)


def prorate_fixed_charges(sales_order: Document, share: float) -> None:
	"""Scale the fixed additional discount and Actual charges; percentage-based ones scale by themselves."""
	if not sales_order.additional_discount_percentage:
		sales_order.discount_amount = flt(
			flt(sales_order.discount_amount) * share, sales_order.precision("discount_amount")
		)
	for tax in sales_order.taxes:
		if tax.charge_type == "Actual":
			tax.tax_amount = flt(flt(tax.tax_amount) * share, tax.precision("tax_amount"))


def validate_feature_enabled() -> None:
	if not frappe.db.get_single_value("Selling Settings", "enable_proforma_invoice"):
		frappe.throw(_("Proforma Invoice is not enabled in Selling Settings."))
