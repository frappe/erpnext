# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import cint, flt, fmt_money, get_link_to_form, getdate
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
		if not (self.from_date and self.to_date):
			frappe.throw(_("From Date and To Date are Mandatory"))

		if not self.account:
			frappe.throw(_("Account is mandatory to get payment entries"))

		entries = []

		# get entries from all the apps
		precision = cint(frappe.db.get_default("currency_precision")) or 2
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

	@frappe.whitelist()
	def update_clearance_date(self):
		invalid_document = []
		invalid_cheque_date = []
		entries_to_update = []

		def validate_entry(d):
			is_valid = True
			if not d.payment_document:
				invalid_document.append(str(d.idx))
				is_valid = False

			if d.clearance_date and d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
				invalid_cheque_date.append(str(d.idx))
				is_valid = False

			return is_valid

		for d in self.get("payment_entries"):
			if validate_entry(d) and (d.clearance_date or self.include_reconciled_entries):
				if not d.clearance_date:
					d.clearance_date = None

				entries_to_update.append(d)

		if invalid_document or invalid_cheque_date:
			msg = _("<p>Please correct the following row(s):</p><ul>")
			if invalid_document:
				msg += _("<li>Payment document required for row(s): {0}</li>").format(
					", ".join(invalid_document)
				)

			if invalid_cheque_date:
				msg += _("<li>Clearance date must be after cheque date for row(s): {0}</li>").format(
					", ".join(invalid_cheque_date)
				)

			msg += "</ul>"
			frappe.throw(_(msg))
			return

		if not entries_to_update:
			msgprint(_("Clearance Date not mentioned"))
			return

		for d in entries_to_update:
			if d.payment_document == "Sales Invoice":
				frappe.db.set_value(
					"Sales Invoice Payment",
					{"parent": d.payment_entry, "account": self.get("account"), "amount": [">", 0]},
					"clearance_date",
					d.clearance_date,
				)
			else:
				# using db_set to trigger notification
				payment_entry = frappe.get_lazy_doc(d.payment_document, d.payment_entry)
				payment_entry.db_set("clearance_date", d.clearance_date)

		self.get_payment_entries()
		msgprint(_("Clearance Date updated"))


def get_payment_entries_for_bank_clearance(
	from_date, to_date, account, bank_account, include_reconciled_entries, include_pos_transactions
):
	entries = []

	condition = ""
	pe_condition = ""
	if not include_reconciled_entries:
		condition = "and (clearance_date IS NULL or clearance_date='0000-00-00')"
		pe_condition = "and (pe.clearance_date IS NULL or pe.clearance_date='0000-00-00')"

	journal_entries = frappe.db.sql(
		f"""
			select
				"Journal Entry" as payment_document, t1.name as payment_entry,
				t1.cheque_no as cheque_number, t1.cheque_date,
				sum(t2.debit_in_account_currency) as debit, sum(t2.credit_in_account_currency) as credit,
				t1.posting_date, t2.against_account, t1.clearance_date, t2.account_currency
			from
				`tabJournal Entry` t1, `tabJournal Entry Account` t2
			where
				t2.parent = t1.name and t2.account = %(account)s and t1.docstatus=1
				and t1.posting_date >= %(from)s and t1.posting_date <= %(to)s
				and ifnull(t1.is_opening, 'No') = 'No' {condition}
			group by t2.account, t1.name
			order by t1.posting_date ASC, t1.name DESC
		""",
		{"account": account, "from": from_date, "to": to_date},
		as_dict=1,
	)

	payment_entries = frappe.db.sql(
		f"""
			select
				"Payment Entry" as payment_document, pe.name as payment_entry,
				pe.reference_no as cheque_number, pe.reference_date as cheque_date,
				if(pe.paid_from=%(account)s, pe.paid_amount + if(pe.payment_type = 'Pay' and c.default_currency = pe.paid_from_account_currency, pe.base_total_taxes_and_charges, pe.total_taxes_and_charges) , 0) as credit,
				if(pe.paid_from=%(account)s, 0, pe.received_amount + pe.total_taxes_and_charges) as debit,
				pe.posting_date, ifnull(pe.party,if(pe.paid_from=%(account)s,pe.paid_to,pe.paid_from)) as against_account, pe.clearance_date,
				if(pe.paid_to=%(account)s, pe.paid_to_account_currency, pe.paid_from_account_currency) as account_currency
			from `tabPayment Entry` as pe
			join `tabCompany` c on c.name = pe.company
			where
				(pe.paid_from=%(account)s or pe.paid_to=%(account)s) and pe.docstatus=1
				and pe.posting_date >= %(from)s and pe.posting_date <= %(to)s
				{pe_condition}
			order by
				pe.posting_date ASC, pe.name DESC
		""",
		{
			"account": account,
			"from": from_date,
			"to": to_date,
		},
		as_dict=1,
	)

	pos_sales_invoices, pos_purchase_invoices = [], []
	if include_pos_transactions:
		si_payment = frappe.qb.DocType("Sales Invoice Payment")
		si = frappe.qb.DocType("Sales Invoice")
		acc = frappe.qb.DocType("Account")

		pos_sales_invoices = (
			frappe.qb.from_(si_payment)
			.inner_join(si)
			.on(si_payment.parent == si.name)
			.inner_join(acc)
			.on(si_payment.account == acc.name)
			.select(
				ConstantColumn("Sales Invoice").as_("payment_document"),
				si.name.as_("payment_entry"),
				si_payment.reference_no.as_("cheque_number"),
				si_payment.amount.as_("debit"),
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
			.orderby(si.posting_date)
			.orderby(si.name, order=Order.desc)
		).run(as_dict=True)

		pi = frappe.qb.DocType("Purchase Invoice")

		pos_purchase_invoices = (
			frappe.qb.from_(pi)
			.inner_join(acc)
			.on(pi.cash_bank_account == acc.name)
			.select(
				ConstantColumn("Purchase Invoice").as_("payment_document"),
				pi.name.as_("payment_entry"),
				pi.paid_amount.as_("credit"),
				pi.posting_date,
				pi.supplier.as_("against_account"),
				pi.clearance_date,
				acc.account_currency,
				ConstantColumn(0).as_("debit"),
			)
			.where(
				(pi.docstatus == 1)
				& (pi.cash_bank_account == account)
				& (pi.posting_date >= from_date)
				& (pi.posting_date <= to_date)
			)
			.orderby(pi.posting_date)
			.orderby(pi.name, order=Order.desc)
		).run(as_dict=True)

	entries = (
		list(payment_entries) + list(journal_entries) + list(pos_sales_invoices) + list(pos_purchase_invoices)
	)

	return entries
