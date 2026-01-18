# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder import functions as fn
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt

from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
	consolidate_pos_invoices,
	unconsolidate_pos_invoices,
)
from erpnext.controllers.status_updater import StatusUpdater


class POSClosingEntry(StatusUpdater):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pos_closing_entry_detail.pos_closing_entry_detail import (
			POSClosingEntryDetail,
		)
		from erpnext.accounts.doctype.pos_closing_entry_taxes.pos_closing_entry_taxes import (
			POSClosingEntryTaxes,
		)
		from erpnext.accounts.doctype.pos_invoice_reference.pos_invoice_reference import POSInvoiceReference
		from erpnext.accounts.doctype.sales_invoice_reference.sales_invoice_reference import (
			SalesInvoiceReference,
		)

		amended_from: DF.Link | None
		company: DF.Link
		error_message: DF.SmallText | None
		grand_total: DF.Currency
		net_total: DF.Currency
		payment_reconciliation: DF.Table[POSClosingEntryDetail]
		period_end_date: DF.Datetime
		period_start_date: DF.Datetime
		pos_invoices: DF.Table[POSInvoiceReference]
		pos_opening_entry: DF.Link
		pos_profile: DF.Link
		posting_date: DF.Date
		posting_time: DF.Time
		sales_invoices: DF.Table[SalesInvoiceReference]
		status: DF.Literal["Draft", "Submitted", "Queued", "Failed", "Cancelled"]
		taxes: DF.Table[POSClosingEntryTaxes]
		total_quantity: DF.Float
		total_taxes_and_charges: DF.Currency
		user: DF.Link
	# end: auto-generated types

	def validate(self):
		self.set_posting_date_and_time()
		self.fetch_invoice_type()
		self.validate_pos_opening_entry()
		self.validate_invoice_mode()

	def set_posting_date_and_time(self):
		if self.posting_date:
			self.posting_date = frappe.utils.nowdate()
		if self.posting_time:
			self.posting_time = frappe.utils.nowtime()

	def fetch_invoice_type(self):
		self.invoice_type = frappe.db.get_single_value("POS Settings", "invoice_type")

	def validate_pos_opening_entry(self):
		if frappe.db.get_value("POS Opening Entry", self.pos_opening_entry, "status") != "Open":
			frappe.throw(_("Selected POS Opening Entry should be open."), title=_("Invalid Opening Entry"))

	def validate_invoice_mode(self):
		if self.invoice_type == "POS Invoice":
			self.validate_duplicate_pos_invoices()
			self.validate_pos_invoices()

		if self.invoice_type == "Sales Invoice":
			if len(self.pos_invoices) != 0:
				frappe.throw(_("POS Invoices can't be added when Sales Invoice is enabled"))

		self.validate_duplicate_sales_invoices()
		self.validate_sales_invoices()

	def validate_duplicate_pos_invoices(self):
		pos_occurences = {}
		for idx, inv in enumerate(self.pos_invoices, 1):
			pos_occurences.setdefault(inv.pos_invoice, []).append(idx)

		error_list = []
		for key, value in pos_occurences.items():
			if len(value) > 1:
				error_list.append(
					_("{0} is added multiple times on rows: {1}").format(frappe.bold(key), frappe.bold(value))
				)

		if error_list:
			frappe.throw(error_list, title=_("Duplicate POS Invoices found"), as_list=True)

	def validate_pos_invoices(self):
		invalid_rows = []
		for d in self.pos_invoices:
			invalid_row = {"idx": d.idx}
			pos_invoice = frappe.db.get_values(
				"POS Invoice",
				d.pos_invoice,
				["consolidated_invoice", "pos_profile", "docstatus", "owner"],
				as_dict=1,
			)[0]
			if pos_invoice.consolidated_invoice:
				invalid_row.setdefault("msg", []).append(_("POS Invoice is already consolidated"))
				invalid_rows.append(invalid_row)
				continue
			if pos_invoice.pos_profile != self.pos_profile:
				invalid_row.setdefault("msg", []).append(
					_("POS Profile doesn't match {}").format(frappe.bold(self.pos_profile))
				)
			if pos_invoice.docstatus != 1:
				invalid_row.setdefault("msg", []).append(_("POS Invoice is not submitted"))
			if pos_invoice.owner != self.user:
				invalid_row.setdefault("msg", []).append(
					_("POS Invoice isn't created by user {}").format(frappe.bold(self.owner))
				)

			if invalid_row.get("msg"):
				invalid_rows.append(invalid_row)

		if not invalid_rows:
			return

		error_list = []
		for row in invalid_rows:
			for msg in row.get("msg"):
				error_list.append(_("Row #{}: {}").format(row.get("idx"), msg))

		frappe.throw(error_list, title=_("Invalid POS Invoices"), as_list=True)

	def validate_duplicate_sales_invoices(self):
		sales_invoice_occurrences = {}
		for idx, inv in enumerate(self.sales_invoices, 1):
			sales_invoice_occurrences.setdefault(inv.sales_invoice, []).append(idx)

		error_list = []
		for key, value in sales_invoice_occurrences.items():
			if len(value) > 1:
				error_list.append(
					_("{0} is added multiple times on rows: {1}").format(frappe.bold(key), frappe.bold(value))
				)

		if error_list:
			frappe.throw(error_list, title=_("Duplicate Sales Invoices found"), as_list=True)

	def validate_sales_invoices(self):
		invalid_rows = []
		for d in self.sales_invoices:
			invalid_row = {"idx": d.idx}
			sales_invoice = frappe.db.get_values(
				"Sales Invoice",
				d.sales_invoice,
				[
					"pos_profile",
					"docstatus",
					"is_pos",
					"owner",
					"is_created_using_pos",
					"is_consolidated",
					"pos_closing_entry",
				],
				as_dict=1,
			)[0]
			if sales_invoice.pos_closing_entry:
				invalid_row.setdefault("msg", []).append(_("Sales Invoice is already consolidated"))
				invalid_rows.append(invalid_row)
				continue
			if sales_invoice.is_pos == 0:
				invalid_row.setdefault("msg", []).append(_("Sales Invoice does not have Payments"))
			if sales_invoice.is_created_using_pos == 0:
				invalid_row.setdefault("msg", []).append(_("Sales Invoice is not created using POS"))
			if sales_invoice.pos_profile != self.pos_profile:
				invalid_row.setdefault("msg", []).append(
					_("POS Profile doesn't match {}").format(frappe.bold(self.pos_profile))
				)
			if sales_invoice.docstatus != 1:
				invalid_row.setdefault("msg", []).append(_("Sales Invoice is not submitted"))
			if sales_invoice.owner != self.user:
				invalid_row.setdefault("msg", []).append(
					_("Sales Invoice isn't created by user {}").format(frappe.bold(self.owner))
				)

			if invalid_row.get("msg"):
				invalid_rows.append(invalid_row)

		if not invalid_rows:
			return

		error_list = []
		for row in invalid_rows:
			for msg in row.get("msg"):
				error_list.append(_("Row #{}: {}").format(row.get("idx"), msg))

		frappe.throw(error_list, title=_("Invalid Sales Invoices"), as_list=True)

	def on_submit(self):
		consolidate_pos_invoices(closing_entry=self)
		frappe.publish_realtime(
			f"poe_{self.pos_opening_entry}",
			message={"operation": "Closed", "doc": self},
			docname=f"POS Opening Entry/{self.pos_opening_entry}",
		)

		self.update_sales_invoices_closing_entry()

	def before_cancel(self):
		self.check_pce_is_cancellable()

	def on_cancel(self):
		unconsolidate_pos_invoices(closing_entry=self)

		self.update_sales_invoices_closing_entry(cancel=True)

	@frappe.whitelist()
	def retry(self):
		consolidate_pos_invoices(closing_entry=self)

	def update_opening_entry(self, for_cancel=False):
		opening_entry = frappe.get_doc("POS Opening Entry", self.pos_opening_entry)
		opening_entry.pos_closing_entry = self.name if not for_cancel else None
		opening_entry.set_status()
		opening_entry.save()

	def update_sales_invoices_closing_entry(self, cancel=False):
		for d in self.sales_invoices:
			frappe.db.set_value(
				"Sales Invoice", d.sales_invoice, "pos_closing_entry", self.name if not cancel else None
			)

	def check_pce_is_cancellable(self):
		if frappe.db.exists("POS Opening Entry", {"pos_profile": self.pos_profile, "status": "Open"}):
			frappe.throw(
				title=_("Cannot cancel POS Closing Entry"),
				msg=_(
					"POS Profile - {0} is currently open. Please close the POS or cancel the existing POS Opening Entry before cancelling this POS Closing Entry."
				).format(frappe.bold(self.pos_profile)),
			)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_cashiers(doctype, txt, searchfield, start, page_len, filters):
	cashiers_list = frappe.get_all("POS Profile User", filters=filters, fields=["user"], as_list=1)
	return [c for c in cashiers_list]


@frappe.whitelist()
def get_invoices(start, end, pos_profile, user):
	invoice_doctype = frappe.db.get_single_value("POS Settings", "invoice_type")

	sales_inv_query = build_invoice_query("Sales Invoice", user, pos_profile, start, end)

	query = sales_inv_query

	if invoice_doctype == "POS Invoice":
		pos_inv_query = build_invoice_query("POS Invoice", user, pos_profile, start, end)
		query = query + pos_inv_query

	query = query.orderby(query.timestamp)
	invoices = query.run(as_dict=1)

	data = {"invoices": invoices, "payments": get_payments(invoices), "taxes": get_taxes(invoices)}

	return data


def get_payments(invoices):
	if not len(invoices):
		return []

	invoices_name = [d.name for d in invoices]

	SalesInvoicePayment = DocType("Sales Invoice Payment")
	query = (
		frappe.qb.from_(SalesInvoicePayment)
		.where(
			(SalesInvoicePayment.parenttype.isin(["Sales Invoice", "POS Invoice"]))
			& (SalesInvoicePayment.parent.isin(invoices_name))
		)
		.groupby(SalesInvoicePayment.mode_of_payment)
		.select(
			SalesInvoicePayment.mode_of_payment,
			SalesInvoicePayment.account,
			fn.Sum(SalesInvoicePayment.amount).as_("amount"),
		)
	)
	data = query.run(as_dict=1)

	change_amount_by_account = {}
	for d in invoices:
		change_amount_by_account.setdefault(d.account_for_change_amount, 0)
		change_amount_by_account[d.account_for_change_amount] += flt(d.change_amount)

	for d in data:
		if change_amount_by_account.get(d.account):
			d.amount -= flt(change_amount_by_account.get(d.account))

	return data


def get_taxes(invoices):
	if not len(invoices):
		return []

	invoices_name = [d.name for d in invoices]

	SalesInvoiceTaxesCharges = DocType("Sales Taxes and Charges")
	query = (
		frappe.qb.from_(SalesInvoiceTaxesCharges)
		.where(
			(SalesInvoiceTaxesCharges.parenttype.isin(["Sales Invoice", "POS Invoice"]))
			& (SalesInvoiceTaxesCharges.parent.isin(invoices_name))
		)
		.groupby(SalesInvoiceTaxesCharges.account_head)
		.select(
			SalesInvoiceTaxesCharges.account_head,
			fn.Sum(SalesInvoiceTaxesCharges.tax_amount_after_discount_amount).as_("tax_amount"),
		)
	)
	data = query.run(as_dict=1)

	return data


def make_closing_entry_from_opening(opening_entry):
	closing_entry = frappe.new_doc("POS Closing Entry")
	closing_entry.pos_opening_entry = opening_entry.name
	closing_entry.period_start_date = opening_entry.period_start_date
	closing_entry.period_end_date = frappe.utils.get_datetime()
	closing_entry.pos_profile = opening_entry.pos_profile
	closing_entry.user = opening_entry.user
	closing_entry.company = opening_entry.company
	closing_entry.grand_total = 0
	closing_entry.net_total = 0
	closing_entry.total_quantity = 0
	closing_entry.total_taxes_and_charges = 0

	data = get_invoices(
		closing_entry.period_start_date,
		closing_entry.period_end_date,
		closing_entry.pos_profile,
		closing_entry.user,
	)

	pos_invoices = []
	sales_invoices = []
	taxes = [
		frappe._dict({"account_head": tx.account_head, "amount": tx.tax_amount}) for tx in data.get("taxes")
	]
	payments = [
		frappe._dict(
			{
				"mode_of_payment": p.mode_of_payment,
				"opening_amount": 0,
				"expected_amount": p.amount,
			}
		)
		for p in data.get("payments")
	]

	for d in data.get("invoices"):
		invoice = "pos_invoice" if d.doctype == "POS Invoice" else "sales_invoice"
		invoice_data = frappe._dict(
			{
				invoice: d.name,
				"posting_date": d.posting_date,
				"grand_total": d.grand_total,
				"customer": d.customer,
				"is_return": d.is_return,
				"return_against": d.return_against,
			}
		)
		if d.doctype == "POS Invoice":
			pos_invoices.append(invoice_data)
		else:
			sales_invoices.append(invoice_data)

		closing_entry.grand_total += flt(d.grand_total)
		closing_entry.net_total += flt(d.net_total)
		closing_entry.total_quantity += flt(d.total_qty)
		closing_entry.total_taxes_and_charges += flt(d.total_taxes_and_charges)

	closing_entry.set("pos_invoices", pos_invoices)
	closing_entry.set("sales_invoices", sales_invoices)
	closing_entry.set("payment_reconciliation", payments)
	closing_entry.set("taxes", taxes)

	return closing_entry


def build_invoice_query(invoice_doctype, user, pos_profile, start, end):
	InvoiceDocType = DocType(invoice_doctype)
	query = (
		frappe.qb.from_(InvoiceDocType)
		.select(
			InvoiceDocType.name,
			InvoiceDocType.customer,
			InvoiceDocType.posting_date,
			InvoiceDocType.grand_total,
			InvoiceDocType.net_total,
			InvoiceDocType.total_qty,
			InvoiceDocType.total_taxes_and_charges,
			InvoiceDocType.change_amount,
			InvoiceDocType.account_for_change_amount,
			InvoiceDocType.is_return,
			InvoiceDocType.return_against,
			fn.Timestamp(InvoiceDocType.posting_date, InvoiceDocType.posting_time).as_("timestamp"),
			ConstantColumn(invoice_doctype).as_("doctype"),
		)
		.where(
			(InvoiceDocType.owner == user)
			& (InvoiceDocType.docstatus == 1)
			& (InvoiceDocType.is_pos == 1)
			& (InvoiceDocType.pos_profile == pos_profile)
			& (
				(fn.Timestamp(InvoiceDocType.posting_date, InvoiceDocType.posting_time) >= start)
				& (fn.Timestamp(InvoiceDocType.posting_date, InvoiceDocType.posting_time) <= end)
			)
		)
	)

	if invoice_doctype == "POS Invoice":
		query = query.where(fn.IfNull(InvoiceDocType.consolidated_invoice, "").eq(""))
	else:
		query = query.where(
			(InvoiceDocType.is_created_using_pos == 1)
			& fn.IfNull(InvoiceDocType.pos_closing_entry, "").eq("")
		)

	return query
