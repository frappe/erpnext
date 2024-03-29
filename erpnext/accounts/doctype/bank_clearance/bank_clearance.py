# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt, fmt_money, getdate
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

			formatted_amount = fmt_money(abs(amount), 2, d.account_currency)
			d.amount = formatted_amount + " " + (_("Dr") if amount > 0 else _("Cr"))
			d.posting_date = getdate(d.posting_date)

			d.pop("credit")
			d.pop("debit")
			d.pop("account_currency")
			row.update(d)

	@frappe.whitelist()
	def update_clearance_date(self):
		clearance_date_updated = False
		for d in self.get("payment_entries"):
			if d.clearance_date:
				if not d.payment_document:
					frappe.throw(_("Row #{0}: Payment document is required to complete the transaction"))

				if d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
					frappe.throw(
						_("Row #{0}: Clearance date {1} cannot be before Cheque Date {2}").format(
							d.idx, d.clearance_date, d.cheque_date
						)
					)

			if d.clearance_date or self.include_reconciled_entries:
				if not d.clearance_date:
					d.clearance_date = None

				payment_entry = frappe.get_doc(d.payment_document, d.payment_entry)
				payment_entry.db_set("clearance_date", d.clearance_date)

				clearance_date_updated = True

		if clearance_date_updated:
			self.get_payment_entries()
			msgprint(_("Clearance Date updated"))
		else:
			msgprint(_("Clearance Date not mentioned"))


def get_payment_entries_for_bank_clearance(
	from_date, to_date, account, bank_account, include_reconciled_entries, include_pos_transactions
):
	entries = []

	condition = ""
	if not include_reconciled_entries:
		condition = "and (clearance_date IS NULL or clearance_date='0000-00-00')"

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

	if bank_account:
		condition += "and bank_account = %(bank_account)s"

	payment_entries = frappe.db.sql(
		f"""
			select
				"Payment Entry" as payment_document, name as payment_entry,
				reference_no as cheque_number, reference_date as cheque_date,
				if(paid_from=%(account)s, paid_amount + total_taxes_and_charges, 0) as credit,
				if(paid_from=%(account)s, 0, received_amount) as debit,
				posting_date, ifnull(party,if(paid_from=%(account)s,paid_to,paid_from)) as against_account, clearance_date,
				if(paid_to=%(account)s, paid_to_account_currency, paid_from_account_currency) as account_currency
			from `tabPayment Entry`
			where
				(paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
				and posting_date >= %(from)s and posting_date <= %(to)s
				{condition}
			order by
				posting_date ASC, name DESC
		""",
		{
			"account": account,
			"from": from_date,
			"to": to_date,
			"bank_account": bank_account,
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
