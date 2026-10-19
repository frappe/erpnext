# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import cint, flt, fmt_money, getdate
from pypika import Order

import erpnext

form_grid_templates = {"journal_entries": "templates/form_grid/bank_reconciliation_grid.html"}


class BankClearance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.bank_clearance_detail.bank_clearance_detail import (
			BankClearanceDetail,
		)

		account: DF.Link
		account_currency: DF.Link | None
		bank_account: DF.Link | None
		from_date: DF.Date
		include_pos_transactions: DF.Check
		include_reconciled_entries: DF.Check
		payment_entries: DF.Table[BankClearanceDetail]
		to_date: DF.Date
	# end: auto-generated types

	@frappe.whitelist()
	def get_payment_entries(self):
		entries = self.get_entries_for_account()
		precision = cint(frappe.db.get_default("currency_precision")) or 2

		entries = sorted(
			entries,
			key=lambda k: getdate(k["posting_date"]),
		)

		self.set("payment_entries", [])
		default_currency = erpnext.get_default_currency()

		for d in entries:
			row = self.append("payment_entries", {})

			amount = flt(d.get("debit", 0)) - flt(d.get("credit", 0))

			if not d.get("account_currency"):
				d.account_currency = default_currency

			formatted_amount = fmt_money(abs(amount), precision, d.account_currency)
			d.amount = formatted_amount + " " + (_("Dr") if amount > 0 else _("Cr"))
			d.posting_date = getdate(d.posting_date)

			d.pop("credit")
			d.pop("debit")
			d.pop("account_currency")
			row.update(d)

	def get_entries_for_account(self):
		if not (self.from_date and self.to_date):
			frappe.throw(_("From Date and To Date are Mandatory"))

		if not self.account:
			frappe.throw(_("Account is mandatory to get payment entries"))

		entries = []

		# get entries from all the apps
		for method_name in frappe.get_hooks("get_payment_entries_for_bank_clearance"):
			entries += (
				frappe.get_attr(method_name)(
					self.from_date,
					self.to_date,
					self.account,
					self.bank_account,
					self.include_reconciled_entries,
					self.include_pos_transactions,
				)
				or []
			)

		return entries

	@frappe.whitelist()
	def update_clearance_date(self):
		self.check_permission("write")
<<<<<<< HEAD
		invalid_document = []
		invalid_cheque_date = []
		entries_to_update = []
=======
		frappe.get_doc("Account", self.account).check_permission("read")
		available_entries = {
			(entry.payment_document, entry.payment_entry): entry for entry in self.get_entries_for_account()
		}
		entries_to_update = []
		for row in self.get("payment_entries"):
			if not (row.clearance_date or self.include_reconciled_entries):
				continue
>>>>>>> 3c49e8b (fix(accounts): validate bank clearance voucher updates)

			entry = available_entries.get((row.payment_document, row.payment_entry))
			if not entry:
				frappe.throw(
					_("Row {0}: Voucher is not eligible for clearance with the selected filters.").format(
						row.idx
					),
					title=_("Invalid Voucher"),
				)

			voucher = frappe.get_doc(row.payment_document, row.payment_entry)
			if not row.clearance_date:
				row.clearance_date = None

			validate_clearance_date(
				voucher,
				row.clearance_date,
				self.account,
				row_idx=row.idx,
				cheque_date=entry.get("cheque_date"),
			)

			entries_to_update.append(row)

		if not entries_to_update:
			msgprint(_("Clearance Date not mentioned"))
			return

		for d in entries_to_update:
			if d.payment_document == "Sales Invoice":
				old_clearance_date = frappe.db.get_value(
					"Sales Invoice Payment",
					{
						"parent": d.payment_entry,
						"account": self.account,
						"amount": ["!=", 0],
					},
					"clearance_date",
				)
				if d.clearance_date or old_clearance_date:
					frappe.db.set_value(
						"Sales Invoice Payment",
						{"parent": d.payment_entry, "account": self.get("account"), "amount": ["!=", 0]},
						"clearance_date",
						d.clearance_date,
					)
					sales_invoice = frappe.get_lazy_doc("Sales Invoice", d.payment_entry)
					sales_invoice.add_comment(
						"Comment",
						_("Clearance date changed from {0} to {1} via Bank Clearance Tool").format(
							old_clearance_date, d.clearance_date
						),
					)

			else:
				payment_entry = frappe.get_lazy_doc(d.payment_document, d.payment_entry)
				old_clearance_date = payment_entry.clearance_date

				if d.clearance_date or old_clearance_date:
					# using db_set to trigger notification
					payment_entry.db_set("clearance_date", d.clearance_date)

					payment_entry.add_comment(
						"Comment",
						_("Clearance date changed from {0} to {1} via Bank Clearance Tool").format(
							old_clearance_date, d.clearance_date
						),
					)

		self.get_payment_entries()
		msgprint(_("Clearance Date updated"))


def validate_clearance_date(voucher, clearance_date, account, row_idx=None, cheque_date=None):
	"""Validate manual clearance changes using the stored voucher and bank allocations."""
	voucher.check_permission("read")
	voucher.check_permission("write")
	label = _("Row {0}").format(row_idx) if row_idx else f"{_(voucher.doctype)} {voucher.name}"
	if voucher.docstatus != 1:
		frappe.throw(
			_("{0}: Only submitted vouchers can be cleared.").format(label), title=_("Invalid Voucher")
		)

	clearance_date = getdate(clearance_date) if clearance_date else None
	clearance_dates = (
		[
			payment.clearance_date
			for payment in voucher.payments
			if payment.account == account and payment.amount != 0
		]
		if voucher.doctype == "Sales Invoice"
		else [voucher.clearance_date]
	)
	if all((getdate(date) if date else None) == clearance_date for date in clearance_dates):
		return

	if clearance_date:
		if clearance_date < getdate(voucher.posting_date):
			frappe.throw(
				_("{0}: Clearance date cannot be before posting date.").format(label),
				title=_("Invalid Clearance Date"),
			)
		cheque_date = cheque_date or voucher.get("cheque_date") or voucher.get("reference_date")
		if cheque_date and clearance_date < getdate(cheque_date):
			frappe.throw(
				_("{0}: Clearance date cannot be before cheque date.").format(label),
				title=_("Invalid Clearance Date"),
			)

	transaction = frappe.qb.DocType("Bank Transaction")
	payment = frappe.qb.DocType("Bank Transaction Payments")
	allocated = (
		frappe.qb.from_(transaction)
		.inner_join(payment)
		.on(payment.parent == transaction.name)
		.select(transaction.name)
		.where(
			(transaction.docstatus == 1)
			& (payment.payment_document == voucher.doctype)
			& (payment.payment_entry == voucher.name)
			& (payment.allocated_amount != 0)
		)
		.limit(1)
	)
	if voucher.doctype == "Sales Invoice":
		bank_account = frappe.qb.DocType("Bank Account")
		allocated = allocated.where(
			transaction.bank_account.isin(
				frappe.qb.from_(bank_account).select(bank_account.name).where(bank_account.account == account)
			)
		)
	if allocated.run():
		frappe.throw(
			_(
				"{0}: Unreconcile the voucher from its Bank Transaction before changing the clearance date."
			).format(label),
			title=_("Voucher Already Reconciled"),
		)


def get_payment_entries_for_bank_clearance(
	from_date, to_date, account, bank_account, include_reconciled_entries, include_pos_transactions
):
	entries = []

	journal_entry = frappe.qb.DocType("Journal Entry")
	journal_entry_account = frappe.qb.DocType("Journal Entry Account")

	journal_entry_query = (
		frappe.qb.from_(journal_entry_account)
		.inner_join(journal_entry)
		.on(journal_entry_account.parent == journal_entry.name)
		.select(
			ConstantColumn("Journal Entry").as_("payment_document"),
			journal_entry.name.as_("payment_entry"),
			journal_entry.cheque_no.as_("cheque_number"),
			journal_entry.cheque_date,
			Sum(journal_entry_account.debit_in_account_currency).as_("debit"),
			Sum(journal_entry_account.credit_in_account_currency).as_("credit"),
			journal_entry.posting_date,
			journal_entry_account.against_account,
			journal_entry.clearance_date,
			journal_entry_account.account_currency,
		)
		.where(
			(journal_entry_account.account == account)
			& (journal_entry.docstatus == 1)
			& (journal_entry.posting_date >= from_date)
			& (journal_entry.posting_date <= to_date)
			& (journal_entry.is_opening == "No")
		)
	)

	if not include_reconciled_entries:
		journal_entry_query = journal_entry_query.where(
			(journal_entry.clearance_date.isnull()) | (journal_entry.clearance_date == "0000-00-00")
		)

	journal_entries = (
		journal_entry_query.groupby(journal_entry_account.account, journal_entry.name)
		.orderby(journal_entry.posting_date)
		.orderby(journal_entry.name, order=Order.desc)
	).run(as_dict=True)

	pe = frappe.qb.DocType("Payment Entry")
	company = frappe.qb.DocType("Company")
	payment_entry_query = (
		frappe.qb.from_(pe)
		.join(company)
		.on(pe.company == company.name)
		.select(
			ConstantColumn("Payment Entry").as_("payment_document"),
			pe.name.as_("payment_entry"),
			pe.reference_no.as_("cheque_number"),
			pe.reference_date.as_("cheque_date"),
			(
				Case()
				.when(
					pe.paid_from == account,
					(
						pe.paid_amount
						+ (
							Case()
							.when(
								(pe.payment_type == "Pay")
								& (company.default_currency == pe.paid_from_account_currency),
								pe.base_total_taxes_and_charges,
							)
							.else_(pe.total_taxes_and_charges)
						)
					),
				)
				.else_(0)
			).as_("credit"),
			(
				Case()
				.when(pe.paid_from == account, 0)
				.else_(
					pe.received_amount
					+ (
						Case()
						.when(
							company.default_currency == pe.paid_to_account_currency,
							pe.base_total_taxes_and_charges,
						)
						.else_(pe.total_taxes_and_charges)
					)
				)
			).as_("debit"),
			pe.posting_date,
			Coalesce(pe.party, Case().when(pe.paid_from == account, pe.paid_to).else_(pe.paid_from)).as_(
				"against_account"
			),
			pe.clearance_date,
			(
				Case()
				.when(pe.paid_to == account, pe.paid_to_account_currency)
				.else_(pe.paid_from_account_currency)
			).as_("account_currency"),
		)
		.where(
			((pe.paid_from == account) | (pe.paid_to == account))
			& (pe.docstatus == 1)
			& (pe.posting_date >= from_date)
			& (pe.posting_date <= to_date)
		)
	)

	if not include_reconciled_entries:
		payment_entry_query = payment_entry_query.where(
			(pe.clearance_date.isnull()) | (pe.clearance_date == "0000-00-00")
		)

	payment_entries = (payment_entry_query.orderby(pe.posting_date).orderby(pe.name, order=Order.desc)).run(
		as_dict=True
	)

	acc = frappe.qb.DocType("Account")

	pi = frappe.qb.DocType("Purchase Invoice")

	paid_purchase_invoices_query = (
		frappe.qb.from_(pi)
		.inner_join(acc)
		.on(pi.cash_bank_account == acc.name)
		.inner_join(company)
		.on(pi.company == company.name)
		.select(
			ConstantColumn("Purchase Invoice").as_("payment_document"),
			pi.name.as_("payment_entry"),
			(
				Case()
				.when(acc.account_currency == company.default_currency, pi.base_paid_amount)
				.else_(pi.paid_amount)
			).as_("credit"),
			pi.posting_date,
			pi.supplier.as_("against_account"),
			pi.bill_no.as_("cheque_number"),
			pi.clearance_date,
			acc.account_currency,
			ConstantColumn(0).as_("debit"),
		)
		.where(
			(pi.docstatus == 1)
			& (pi.is_paid == 1)
			& (pi.cash_bank_account == account)
			& (pi.posting_date >= from_date)
			& (pi.posting_date <= to_date)
		)
	)

	if not include_reconciled_entries:
		paid_purchase_invoices_query = paid_purchase_invoices_query.where(
			(pi.clearance_date.isnull()) | (pi.clearance_date == "0000-00-00")
		)

	paid_purchase_invoices = (
		paid_purchase_invoices_query.orderby(pi.posting_date).orderby(pi.name, order=Order.desc)
	).run(as_dict=True)

	pos_sales_invoices = []

	if include_pos_transactions:
		si_payment = frappe.qb.DocType("Sales Invoice Payment")
		si = frappe.qb.DocType("Sales Invoice")

		pos_sales_invoices_query = (
			frappe.qb.from_(si_payment)
			.inner_join(si)
			.on(si_payment.parent == si.name)
			.inner_join(acc)
			.on(si_payment.account == acc.name)
			.inner_join(company)
			.on(si.company == company.name)
			.select(
				ConstantColumn("Sales Invoice").as_("payment_document"),
				si.name.as_("payment_entry"),
				si_payment.reference_no.as_("cheque_number"),
				(
					Case()
					.when(acc.account_currency == company.default_currency, si_payment.base_amount)
					.else_(si_payment.amount)
				).as_("debit"),
				si.posting_date,
				si.customer.as_("against_account"),
				si_payment.clearance_date,
				acc.account_currency,
				ConstantColumn(0).as_("credit"),
			)
			.where(
				(si.docstatus == 1)
				& (si_payment.account == account)
				& (si.posting_date >= from_date)
				& (si.posting_date <= to_date)
			)
		)

		if not include_reconciled_entries:
			pos_sales_invoices_query = pos_sales_invoices_query.where(
				(si_payment.clearance_date.isnull()) | (si_payment.clearance_date == "0000-00-00")
			)

		pos_sales_invoices = (
			pos_sales_invoices_query.orderby(si.posting_date).orderby(si.name, order=Order.desc)
		).run(as_dict=True)

	entries = (
		list(payment_entries)
		+ list(journal_entries)
		+ list(pos_sales_invoices)
		+ list(paid_purchase_invoices)
	)

	return entries
