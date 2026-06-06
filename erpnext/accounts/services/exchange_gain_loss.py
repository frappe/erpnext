# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Exchange gain/loss journal helpers."""

import frappe
from frappe import _, qb
from frappe.utils import flt, get_link_to_form

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.utils import create_gain_loss_journal, get_currency_precision


def gain_loss_journal_already_booked(
	gain_loss_account: str,
	exc_gain_loss: float,
	ref2_dt: str,
	ref2_dn: str,
	ref2_detail_no: str,
) -> bool:
	"""Check if a gain/loss journal has already been booked for the given parameters."""
	if res := frappe.db.get_all(
		"Journal Entry Account",
		filters={
			"docstatus": 1,
			"account": gain_loss_account,
			"reference_type": ref2_dt,
			"reference_name": ref2_dn,
			"reference_detail_no": ref2_detail_no,
		},
		pluck="parent",
	):
		res = list({x for x in res})
		if exc_vouchers := frappe.db.get_all(
			"Journal Entry",
			filters={"name": ["in", res], "voucher_type": "Exchange Gain Or Loss"},
			fields=["voucher_type", "total_debit", "total_credit"],
		):
			booked_voucher = exc_vouchers[0]
			if (
				booked_voucher.total_debit == exc_gain_loss
				and booked_voucher.total_credit == exc_gain_loss
				and booked_voucher.voucher_type == "Exchange Gain Or Loss"
			):
				return True
	return False


def make_exchange_gain_loss_journal(
	doc, args: dict | None = None, dimensions_dict: dict | None = None
) -> None:
	"""Make Exchange Gain/Loss journal for Invoices and Payments."""
	# Cancelling existing exchange gain/loss journals is handled during the `on_cancel` event.
	# see accounts/utils.py:cancel_exchange_gain_loss_journal()
	if doc.docstatus != 1:
		return

	if dimensions_dict is None:
		dimensions_dict = frappe._dict()
		active_dimensions = get_dimensions()[0]
		for dim in active_dimensions:
			dimensions_dict[dim.fieldname] = doc.get(dim.fieldname)

	if doc.get("doctype") == "Journal Entry":
		if args:
			precision = get_currency_precision()
			for arg in args:
				if (
					flt(arg.get("difference_amount", 0), precision) != 0
					or flt(arg.get("exchange_gain_loss", 0), precision) != 0
				) and arg.get("difference_account"):
					party_account = arg.get("account")
					gain_loss_account = arg.get("difference_account")
					difference_amount = arg.get("difference_amount") or arg.get("exchange_gain_loss")
					if difference_amount > 0:
						dr_or_cr = "debit" if arg.get("party_type") == "Customer" else "credit"
					else:
						dr_or_cr = "credit" if arg.get("party_type") == "Customer" else "debit"

					reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

					if not gain_loss_journal_already_booked(
						gain_loss_account,
						difference_amount,
						doc.doctype,
						doc.name,
						arg.get("referenced_row"),
					):
						posting_date = arg.get("difference_posting_date") or frappe.db.get_value(
							arg.voucher_type, arg.voucher_no, "posting_date"
						)
						je = create_gain_loss_journal(
							doc.company,
							posting_date,
							arg.get("party_type"),
							arg.get("party"),
							party_account,
							gain_loss_account,
							difference_amount,
							dr_or_cr,
							reverse_dr_or_cr,
							arg.get("against_voucher_type"),
							arg.get("against_voucher"),
							arg.get("idx"),
							doc.doctype,
							doc.name,
							arg.get("referenced_row"),
							arg.get("cost_center"),
							dimensions_dict,
							arg.get("project"),
						)
						frappe.msgprint(
							_("Exchange Gain/Loss amount has been booked through {0}").format(
								get_link_to_form("Journal Entry", je)
							)
						)

	if doc.get("doctype") == "Payment Entry":
		gain_loss_to_book = [x for x in doc.references if x.exchange_gain_loss != 0]
		booked = []
		if gain_loss_to_book:
			je = qb.DocType("Journal Entry")
			jea = qb.DocType("Journal Entry Account")
			parents = (
				qb.from_(jea)
				.select(jea.parent)
				.where(
					(jea.reference_type == "Payment Entry")
					& (jea.reference_name == doc.name)
					& (jea.docstatus == 1)
				)
				.run()
			)

			if parents:
				booked = (
					qb.from_(je)
					.inner_join(jea)
					.on(je.name == jea.parent)
					.select(jea.reference_type, jea.reference_name, jea.reference_detail_no)
					.where(
						(je.docstatus == 1)
						& (je.name.isin(parents))
						& (je.voucher_type == "Exchange Gain or Loss")
					)
					.run()
				)

		for d in gain_loss_to_book:
			if d.exchange_gain_loss and ((d.reference_doctype, d.reference_name, str(d.idx)) not in booked):
				if doc.book_advance_payments_in_separate_party_account:
					party_account = d.account
				else:
					if doc.payment_type == "Receive":
						party_account = doc.paid_from
					elif doc.payment_type == "Pay":
						party_account = doc.paid_to

				dr_or_cr = "debit" if d.exchange_gain_loss > 0 else "credit"

				if is_payable_account(d.reference_doctype, party_account):
					dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

				reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

				gain_loss_account = frappe.get_cached_value(
					"Company", doc.company, "exchange_gain_loss_account"
				)
				je = create_gain_loss_journal(
					doc.company,
					args.get("difference_posting_date") if args else doc.posting_date,
					doc.party_type,
					doc.party,
					party_account,
					gain_loss_account,
					d.exchange_gain_loss,
					dr_or_cr,
					reverse_dr_or_cr,
					d.reference_doctype,
					d.reference_name,
					d.idx,
					doc.doctype,
					doc.name,
					d.idx,
					doc.cost_center,
					dimensions_dict,
					doc.project,
				)
				frappe.msgprint(
					_("Exchange Gain/Loss amount has been booked through {0}").format(
						get_link_to_form("Journal Entry", je)
					)
				)


def is_payable_account(reference_doctype: str, account: str) -> bool:
	if reference_doctype == "Purchase Invoice" or (
		reference_doctype == "Journal Entry"
		and frappe.get_cached_value("Account", account, "account_type") == "Payable"
	):
		return True
	return False


def set_transaction_currency_and_rate_in_gl_map(doc, gl_entries: list) -> None:
	for entry in gl_entries:
		entry["transaction_currency"] = doc.currency
		entry["transaction_exchange_rate"] = doc.get("conversion_rate") or 1
