# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.status_updater import StatusUpdater
from frappe.utils import flt
from six.moves import reduce
from frappe import _

class BankTransaction(StatusUpdater):
	def after_insert(self):
		self.unallocated_amount = abs(flt(self.credit) - flt(self.debit))

	def on_submit(self):
		self.clear_linked_payment_entries()
		self.set_status()

	def on_update_after_submit(self):
		self.update_allocations()
		self.clear_linked_payment_entries()
		self.set_status(update=True)

	def update_allocations(self):
		if self.payment_entries:
			allocated_amount = reduce(lambda x, y: flt(x) + flt(y), [x.allocated_amount for x in self.payment_entries])
		else:
			allocated_amount = 0

		if allocated_amount:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", flt(allocated_amount))
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)) - flt(allocated_amount))

		else:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", 0)
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)))

		amount = self.debit or self.credit
		if amount == self.allocated_amount:
			frappe.db.set_value(self.doctype, self.name, "status", "Reconciled")

		self.reload()

	def clear_linked_payment_entries(self):
		for payment_entry in self.payment_entries:
			allocated_amount = get_total_allocated_amount(payment_entry)
			paid_amount = self.get_paid_amount(payment_entry.payment_document,
				payment_entry.payment_entry, self.currency)

			if paid_amount and allocated_amount:
				if  flt(allocated_amount[0]["allocated_amount"]) > flt(paid_amount):
					frappe.throw(_("The total allocated amount ({0}) is greater than the paid amount ({1}).").format(flt(allocated_amount[0]["allocated_amount"]), flt(paid_amount)))
				else:
					# LEGACY: it is still possible that there are
					# Bank Transaction records out there in old
					# databases with Journal Entry or Sales Invoice
					# payment entries. So to be on the safe side,
					# handle clearing them even though new entries
					# like that cannot be created.
					if payment_entry.payment_document in ["Sales Invoice", "Journal Entry"]:
						return self.clear_legacy_entry(payment_entry)
					self.clear_simple_entry(payment_entry.payment_document,
						payment_entry.payment_entry)

	def clear_simple_entry(self, entry_type, entry_name):
		frappe.db.set_value(entry_type, entry_name, "clearance_date", self.date)
		if entry_type == "Journal Entry Account":
			frappe.db.set_value("Journal Entry Account", entry_name,
				"reconciled_with", self.name)

	def clear_legacy_entry(self, payment_entry):
		if payment_entry.payment_document == "Sales Invoice":
			frappe.db.set_value("Sales Invoice Payment",
				dict(parenttype=payment_entry.payment_document,
					parent=payment_entry.payment_entry
				), "clearance_date", self.date
			)
		else:  # Journal Entry
			je = frappe.get_doc("Journal Entry", payment_entry.payment_entry);
			account = frappe.db.get_value("Bank Account", self.bank_account,
				"account")
			for jea in je.accounts:
				if jea.account == account:
					self.clear_simple_entry("Journal Entry Account",
						jea.name)

	def get_paid_amount(self, entry_type, entry_name, currency):
		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		# First deal with the currently-used types of payment documents:
		if entry_type in ["Payment Entry", "Purchase Invoice"]:
			paid_amount_field = "paid_amount"
			if entry_type == 'Payment Entry':
				account = frappe.db.get_value("Bank Account", self.bank_account, "account")
				doc = frappe.get_doc("Payment Entry", entry_name)
				if doc.paid_from == account:
					if doc.paid_from_account_currency == currency:
						paid_amount_field = "paid_amount"
					elif company_currency == currency:
						paid_amount_field = "base_paid_amount"
					else:
						frappe.throw(_("Unable to determine amount of {0} {1} in {2}").format(entry_type, entry_name, currency))
				elif doc.paid_to == account:
					if doc.paid_to_account_currency == currency:
						paid_amount_field = "received_amount"
					elif company_currency == currency:
						paid_amount_field = "base_received_amount"
					else:
						frappe.throw(_("Unable to determine amount of {0} {1} in {2}").format(entry_type, currency))
				else:
					frappe.throw(_("Payment Entry {0} does not match Bank Account of {1}").format(entry_name, self.name))
			else:
				if doc.currency == currency:
					paid_amount_field = "paid_amount"
				elif company_currency == currency:
					paid_amount_field = "base_paid_amount"
				else:
					frappe.throw(_("Unable to determine amount of {0} {1} in {2}").format(entry_type, currency))
			return frappe.db.get_value(entry_type, entry_name, paid_amount_field)

		elif entry_type == "Sales Invoice Payment":
			doc = frappe.get_doc("Sales Invoice Payment", entry_name)
			if frappe.db.get_value("Sales Invoice", doc.parent, "currency") == currency:
				paid_amount_field = "amount"
			elif company_currency == currency:
				paid_amount_field = "base_amount"
			else:
				frappe.throw(_("Unable to determine amount of {0} {1} in {2}").format(entry_type, currency))
			return doc.get(paid_amount_field)
		elif entry_type == "Journal Entry Account":
			doc = frappe.get_doc("Journal Entry Account", entry_name)
			if currency == doc.account_currency:
				return doc.debit_in_account_currency + doc.credit_in_account_currency
			elif currency == company_currency:
				return doc.debit + doc.credit
			else:
				frappe.throw(_("Unable to determine amount of {0} {1} in {2}").format(entry_type, currency))

		# LEGACY: deal with possible remaining instances of older reconciliation types
		elif entry_type == "Expense Claim":
			return frappe.db.get_value("Expense Claim", entry_name, "total_amount_reimbursed")

		elif entry_type == "Sales Invoice" or entry_type == "Journal Entry":
			account = frappe.db.get_value("Bank Account", self.bank_account,
				"account")
			child_type = ("Sales Invoice Payment" if entry_type == "Sales Invoice"
				else "Journal Invoice Account")
			table_name = "payments" if entry_type == "Sales Invoice" else "accounts"

			doc = frappe.get_doc(entry_type, entry_name)
			return sum(self.get_paid_amount(child_type, child.name, currency)
				for child in doc.get(table_name) if child.account == account)

		else:
			frappe.throw("Please reconcile {0}: {1} manually".format(entry_type, entry_name))


def get_total_allocated_amount(payment_entry):
	return frappe.db.sql("""
		SELECT
			SUM(btp.allocated_amount) as allocated_amount,
			bt.name
		FROM
			`tabBank Transaction Payments` as btp
		LEFT JOIN
			`tabBank Transaction` bt ON bt.name=btp.parent
		WHERE
			btp.payment_document = %s
		AND
			btp.payment_entry = %s
		AND
			bt.docstatus = 1""", (payment_entry.payment_document, payment_entry.payment_entry), as_dict=True)

@frappe.whitelist()
def unclear_reference_payment(doctype, docname):
	# Note that the doc passed in here will always be a
	# Bank Tranaction Payments entry and we have to go from it to the
	# actual payment document to unclear:
	if doctype != "Bank Transaction Payments" or not frappe.db.exists("Bank Transaction Payments", docname):
		frappe.throw(f"Inconsistent Bank Transaction payment_entries record: {doctype} named {docname}")
	doc = frappe.get_doc("Bank Transaction Payments", docname)
	if not frappe.db.exists(doc.payment_document, doc.payment_entry):
		frappe.throw(f"Error: no payment entry {doc.payment_document} named {doc.payment_entry}")

	# LEGACY: Deal with older types of payment documents no longer used:
	if doc.payment_document == "Sales Invoice":
		frappe.db.set_value("Sales Invoice Payment",
			dict(parenttype=doc.payment_document, parent=doc.payment_entry),
			"clearance_date", None)
	if doc.payment_document == "Journal Entry":
		frappe.db.set_value(doc.payment_document, doc.payment_entry,
			"clearance_date", None)
		account = frappe.db.get_value("Bank Account",
			frappe.db.get_value("Bank Transaction", doc.parent,
				"bank_account"),
			"account")
		je = frappe.get_doc("Journal Entry", doc.payment_entry)
		for jea in je.accounts:
			if jea.account == account and jea.reconciled_with == doc.parent:
				unclear_reference_payment("Journal Entry Account", jea.name)
	# Deal with all of the current types of payment documents:
	else:
		frappe.db.set_value(doc.payment_document, doc.payment_entry,
			"clearance_date", None)
		if doc.payment_document == "Journal Entry Account":
			frappe.db.set_value("Journal Entry Account", doc.payment_entry,
				"reconciled_with", None)
	return dict(status="success", entry=doc.payment_entry)
