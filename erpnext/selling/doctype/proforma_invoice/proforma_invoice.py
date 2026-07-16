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

		from erpnext.selling.doctype.proforma_invoice_item.proforma_invoice_item import (
			ProformaInvoiceItem,
		)

		amended_from: DF.Link | None
		company: DF.Link
		currency: DF.Link | None
		customer: DF.Link | None
		customer_name: DF.Data | None
		emailed_to: DF.SmallText | None
		grand_total: DF.Currency
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
		self.warn_on_over_proforma_qty()

	def before_submit(self) -> None:
		self.status = "Issued"

	def on_submit(self) -> None:
		self.update_proforma_qty_in_sales_order()
		self.generate_and_attach_pdf()

	def on_cancel(self) -> None:
		self.status = "Cancelled"
		self.update_proforma_qty_in_sales_order()

	def set_total_qty(self) -> None:
		self.total_qty = sum(flt(item.qty) for item in self.items)

	def warn_on_over_proforma_qty(self) -> None:
		"""Soft-warn (never block) if a line exceeds its pending proforma qty."""
		pending = {row["so_detail"]: row["pending_qty"] for row in get_pending_proforma_qty(self.sales_order)}
		for item in self.items:
			if flt(item.qty) > flt(pending.get(item.so_detail)) + 0.0001:
				frappe.msgprint(
					_("Qty {0} for {1} exceeds the pending proforma qty {2}.").format(
						flt(item.qty), item.item_code, flt(pending.get(item.so_detail))
					),
					indicator="orange",
					alert=True,
				)

	def update_proforma_qty_in_sales_order(self) -> None:
		"""Refresh the non-blocking, cosmetic proforma_qty counter on each SO item."""
		qty_map = get_proformed_qty_map(self.sales_order)
		for name in frappe.get_all("Sales Order Item", filters={"parent": self.sales_order}, pluck="name"):
			frappe.db.set_value(
				"Sales Order Item", name, "proforma_qty", flt(qty_map.get(name)), update_modified=False
			)

	def generate_and_attach_pdf(self) -> None:
		if self.proforma_pdf:
			return
		printed = self.render_pdf()
		file = save_file(printed["fname"], printed["fcontent"], self.doctype, self.name, is_private=1)
		self.db_set("proforma_pdf", file.file_url)

	def render_pdf(self) -> dict:
		"""Render the proforma PDF from an in-memory, qty-adjusted copy of the Sales Order.

		The Sales Order copy is never saved; it exists only to reuse the standard tax/total
		calculation and print format so the proforma shows accurate gross for the partial qty.
		"""
		sales_order = frappe.get_doc("Sales Order", self.sales_order)
		qty_by_detail = {item.so_detail: item.qty for item in self.items}
		sales_order.items = [item for item in sales_order.items if item.name in qty_by_detail]
		for item in sales_order.items:
			item.qty = qty_by_detail[item.name]
		sales_order.run_method("calculate_taxes_and_totals")
		sales_order.proforma_no = self.name
		sales_order.proforma_date = self.proforma_date
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
def get_pending_proforma_qty(sales_order: str) -> list[dict]:
	"""Per-SO-line pending proforma qty = ordered qty minus already issued proforma qty."""
	sales_order_doc = frappe.get_doc("Sales Order", sales_order)
	proformed = get_proformed_qty_map(sales_order)
	return [
		{
			"item_code": item.item_code,
			"item_name": item.item_name,
			"uom": item.uom,
			"so_detail": item.name,
			"so_qty": flt(item.qty),
			"pending_qty": flt(item.qty) - flt(proformed.get(item.name)),
		}
		for item in sales_order_doc.items
	]


def get_proformed_qty_map(sales_order: str) -> dict[str, float]:
	"""Sum of issued (docstatus = 1) proforma qty per Sales Order Item row."""
	proformas = frappe.get_all(
		"Proforma Invoice", filters={"sales_order": sales_order, "docstatus": 1}, pluck="name"
	)
	if not proformas:
		return {}
	item = frappe.qb.DocType("Proforma Invoice Item")
	rows = (
		frappe.qb.from_(item)
		.select(item.so_detail, Sum(item.qty).as_("qty"))
		.where(item.parent.isin(proformas))
		.groupby(item.so_detail)
	).run(as_dict=True)
	return {row.so_detail: flt(row.qty) for row in rows}


@frappe.whitelist()
def make_proforma_invoice(
	sales_order: str,
	items: str,
	naming_series: str | None = None,
	print_format: str | None = None,
	letter_head: str | None = None,
) -> str:
	"""The sole creation path for a Proforma Invoice (the doctype is `in_create`)."""
	validate_feature_enabled()
	selected = frappe.parse_json(items)
	sales_order_doc = frappe.get_doc("Sales Order", sales_order)
	so_items = {item.name: item for item in sales_order_doc.items}

	proforma = frappe.new_doc("Proforma Invoice")
	proforma.sales_order = sales_order
	if naming_series:
		proforma.naming_series = naming_series
	proforma.print_format = print_format or frappe.db.get_single_value(
		"Selling Settings", "default_proforma_print_format"
	)
	proforma.letter_head = letter_head

	for row in selected:
		qty = flt(row.get("qty"))
		so_item = so_items.get(row.get("so_detail"))
		if qty <= 0 or not so_item:
			continue
		proforma.append(
			"items",
			{
				"item_code": so_item.item_code,
				"item_name": so_item.item_name,
				"uom": so_item.uom,
				"qty": qty,
				"so_detail": so_item.name,
			},
		)

	if not proforma.items:
		frappe.throw(_("Please enter a quantity for at least one item."))

	proforma.insert()
	proforma.submit()
	return proforma.name


@frappe.whitelist()
def send_proforma_email(proforma_name: str, recipients: str) -> None:
	proforma = frappe.get_doc("Proforma Invoice", proforma_name)
	if not proforma.proforma_pdf:
		frappe.throw(_("This Proforma Invoice has no PDF to send."))

	file_name = frappe.db.get_value("File", {"file_url": proforma.proforma_pdf}, "name")
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
