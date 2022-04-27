# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.utils import now


class PaymentLedgerEntry(Document):
	def validate(self):
		if not self.voucher_no:
			frappe.throw(_("Voucher No is mandatory"))
		if not self.against_voucher_no:
			frappe.throw(_("Against Voucher No is mandatory"))
		if not self.amount:
			frappe.throw(_("Amount is mandatory"))


def reverse_payment_ledger_entry(payment_ledger_entry):
	"""
	payment_ledger_entry - frappe._dict
	"""
	mark_original_as_is_cancelled(payment_ledger_entry)
	payment_ledger_entry.submit()


def save_ple_entries(pl_entries, cancel=0):
	if pl_entries:
		for entry in pl_entries:
			if cancel:
				reverse_payment_ledger_entry(entry)
			else:
				entry.submit()


def get_payment_ledger_entries(gl_map, cancel=0):
	pl_entries = []
	for entry in gl_map:

		if entry.get("against_voucher_type") and entry.get("against_voucher"):
			if entry.get("against_voucher") != entry.get("voucher_no"):

				dr_or_cr = 0
				ple = frappe.get_doc(
					{
						"doctype": "Payment Ledger Entry",
						"posting_date": now(),
						"amount": abs(entry.debit - entry.credit) * -1
						if cancel
						else abs(entry.debit - entry.credit),
						"is_cancelled": cancel,
					}
				)
				# identify transaction type
				if frappe.db.get_value("Account", entry.account, "root_type") == "Asset":
					dr_or_cr = entry.debit - entry.credit
				elif frappe.db.get_value("Account", entry.account, "root_type") == "Liability":
					dr_or_cr = entry.credit - entry.debit

				if dr_or_cr > 0:
					ple.voucher_type = entry.against_voucher_type
					ple.voucher_no = entry.against_voucher
					ple.against_voucher_type = entry.voucher_type
					ple.against_voucher_no = entry.voucher_no
				else:
					ple.voucher_type = entry.voucher_type
					ple.voucher_no = entry.voucher_no
					ple.against_voucher_type = entry.against_voucher_type
					ple.against_voucher_no = entry.against_voucher
				pl_entries.append(ple)
	return pl_entries


def get_active_payments(inv_type, inv_no):
	"""
	fetch all active payments against invoice
	"""
	pledger = frappe.qb.DocType("Payment Ledger Entry")
	active_payments = (
		frappe.qb.from_(pledger)
		.select(
			pledger.voucher_type,
			pledger.voucher_no,
			pledger.against_voucher_type,
			pledger.against_voucher_no,
			pledger.amount,
		)
		.where(
			(pledger.against_voucher_type == inv_type)
			& (pledger.against_voucher_no == inv_no)
			& (pledger.is_cancelled == 0)
		)
		.run(as_dict=True)
	)
	return active_payments


def unlink_invoice_from_payment(inv_type, inv_no):
	"""
	if invoice has payment entry, delink it in payment ledger
	"""
	return
	payments = get_active_payments(inv_type, inv_no)
	for entry in payments:
		reverse_payment_ledger_entry(entry)


def mark_original_as_is_cancelled(payment_ledger_entry):
	pl = qb.DocType("Payment Ledger Entry")
	if payment_ledger_entry:
		(
			qb.update(pl)
			.set(pl.is_cancelled, True)
			.set(pl.modified, now())
			.set(pl.modified_by, frappe.session.user)
			.where(
				(pl.voucher_type == payment_ledger_entry.voucher_type)
				& (pl.voucher_no == payment_ledger_entry.voucher_no)
				& (
					pl.against_voucher_type.isnull()
					if payment_ledger_entry.against_voucher_type is None
					else pl.against_voucher_type == payment_ledger_entry.against_voucher_type
				)
				& (
					pl.against_voucher_no.isnull()
					if payment_ledger_entry.against_voucher_no is None
					else pl.against_voucher_no == payment_ledger_entry.against_voucher_no
				)
				& (pl.is_cancelled == 0)
			)
			.run()
		)
