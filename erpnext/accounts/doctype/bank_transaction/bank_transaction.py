# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.docstatus import DocStatus
from frappe.model.document import Document
from frappe.utils import flt, getdate


class BankTransaction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.bank_transaction_payments.bank_transaction_payments import (
			BankTransactionPayments,
		)

		allocated_amount: DF.Currency
		amended_from: DF.Link | None
		bank_account: DF.Link | None
		bank_party_account_number: DF.Data | None
		bank_party_iban: DF.Data | None
		bank_party_name: DF.Data | None
		company: DF.Link | None
		currency: DF.Link | None
		date: DF.Date | None
		deposit: DF.Currency
		description: DF.SmallText | None
		naming_series: DF.Literal["ACC-BTN-.YYYY.-"]
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		payment_entries: DF.Table[BankTransactionPayments]
		reference_number: DF.SmallText | None
		status: DF.Literal["", "Pending", "Settled", "Unreconciled", "Reconciled", "Cancelled"]
		transaction_id: DF.Data | None
		transaction_type: DF.Data | None
		unallocated_amount: DF.Currency
		withdrawal: DF.Currency
	# end: auto-generated types

	def before_validate(self):
		self.update_allocated_amount()

	def validate(self):
		self.validate_duplicate_references()
		self.validate_currency()

	def validate_currency(self):
		"""
		Bank Transaction should be on the same currency as the Bank Account.
		"""
		if self.currency and self.bank_account:
			if account := frappe.get_cached_value("Bank Account", self.bank_account, "account"):
				account_currency = frappe.get_cached_value("Account", account, "account_currency")

				if self.currency != account_currency:
					frappe.throw(
						_(
							"Transaction currency: {0} cannot be different from Bank Account({1}) currency: {2}"
						).format(
							frappe.bold(self.currency),
							frappe.bold(self.bank_account),
							frappe.bold(account_currency),
						)
					)

	def set_status(self):
		if self.docstatus == 2:
			self.db_set("status", "Cancelled")
		elif self.docstatus == 1:
			if self.unallocated_amount > 0:
				self.db_set("status", "Unreconciled")
			elif self.unallocated_amount <= 0:
				self.db_set("status", "Reconciled")

	def validate_duplicate_references(self):
		"""Make sure the same voucher is not allocated twice within the same Bank Transaction"""
		if not self.payment_entries:
			return

		references = set()
		for row in self.payment_entries:
			reference = (row.payment_document, row.payment_entry)
			if reference in references:
				frappe.throw(
					_("{0} {1} is allocated twice in this Bank Transaction").format(
						row.payment_document, row.payment_entry
					)
				)
			references.add(reference)

	def update_allocated_amount(self):
		allocated_amount = (
			sum(p.allocated_amount for p in self.payment_entries) if self.payment_entries else 0.0
		)
		unallocated_amount = abs(flt(self.withdrawal) - flt(self.deposit)) - allocated_amount

		self.allocated_amount = flt(allocated_amount, self.precision("allocated_amount"))
		self.unallocated_amount = flt(unallocated_amount, self.precision("unallocated_amount"))

	def delink_old_payment_entries(self):
		if self.flags.updating_linked_bank_transaction:
			return

		old_doc = self.get_doc_before_save()
		payment_entry_names = set(pe.name for pe in self.payment_entries)

		for old_pe in old_doc.payment_entries:
			if old_pe.name in payment_entry_names:
				continue

			self.delink_payment_entry(old_pe)

	def before_submit(self):
		self.allocate_payment_entries()
		self.set_status()

		if frappe.get_single_value("Accounts Settings", "enable_party_matching"):
			self.auto_set_party()

	def before_update_after_submit(self):
		self.validate_duplicate_references()
		self.update_allocated_amount()
		self.delink_old_payment_entries()
		self.allocate_payment_entries()
		self.set_status()

	def on_cancel(self):
		for payment_entry in self.payment_entries:
			self.delink_payment_entry(payment_entry)

		self.set_status()

	def add_payment_entries(self, vouchers):
		"Add the vouchers with zero allocation. Save() will perform the allocations and clearance"
		if 0.0 >= self.unallocated_amount:
			frappe.throw(_("Bank Transaction {0} is already fully reconciled").format(self.name))

		for voucher in vouchers:
			self.append(
				"payment_entries",
				{
					"payment_document": voucher["payment_doctype"],
					"payment_entry": voucher["payment_name"],
					"allocated_amount": 0.0,  # Temporary
				},
			)

	def allocate_payment_entries(self):
		"""Refactored from bank reconciliation tool.
		Non-zero allocations must be amended/cleared manually
		Get the bank transaction amount (b) and remove as we allocate
		For each payment_entry if allocated_amount == 0:
		- get the amount already allocated against all transactions (t), need latest date
		- get the voucher amount (from gl) (v)
		- allocate (a = v - t)
		    - a = 0: should already be cleared, so clear & remove payment_entry
		    - 0 < a <= u: allocate a & clear
		    - 0 < a, a > u: allocate u
		    - 0 > a: Error: already over-allocated
		- clear means: set the latest transaction date as clearance date
		"""
		if self.flags.updating_linked_bank_transaction or not self.payment_entries:
			return

		remaining_amount = self.unallocated_amount
		payment_entry_docs = [(pe.payment_document, pe.payment_entry) for pe in self.payment_entries]
		pe_bt_allocations = get_total_allocated_amount(payment_entry_docs)
		gl_entries = get_related_bank_gl_entries(payment_entry_docs)
		gl_bank_account = frappe.db.get_value("Bank Account", self.bank_account, "account")

		for payment_entry in list(self.payment_entries):
			if payment_entry.allocated_amount != 0:
				continue

			allocable_amount, should_clear, clearance_date = get_clearance_details(
				self,
				payment_entry,
				pe_bt_allocations.get((payment_entry.payment_document, payment_entry.payment_entry)) or {},
				gl_entries.get((payment_entry.payment_document, payment_entry.payment_entry)) or {},
				gl_bank_account,
			)

			if allocable_amount < 0:
				frappe.throw(_("Voucher {0} is over-allocated by {1}").format(allocable_amount))

			if remaining_amount <= 0:
				self.remove(payment_entry)
				continue

			if allocable_amount == 0:
				if should_clear:
					self.clear_linked_payment_entry(payment_entry, clearance_date=clearance_date)
				self.remove(payment_entry)
				continue

			should_clear = should_clear and allocable_amount <= remaining_amount
			payment_entry.allocated_amount = min(allocable_amount, remaining_amount)
			remaining_amount = flt(
				remaining_amount - payment_entry.allocated_amount,
				self.precision("unallocated_amount"),
			)

			if payment_entry.payment_document == "Bank Transaction":
				self.update_linked_bank_transaction(
					payment_entry.payment_entry, payment_entry.allocated_amount
				)
			elif should_clear:
				self.clear_linked_payment_entry(payment_entry, clearance_date=clearance_date)

		self.update_allocated_amount()

	@frappe.whitelist()
	def remove_payment_entries(self):
		for payment_entry in self.payment_entries:
			self.remove_payment_entry(payment_entry)

		self.save()  # runs before_update_after_submit

	def remove_payment_entry(self, payment_entry):
		"Clear payment entry and clearance"
		self.delink_payment_entry(payment_entry)
		self.remove(payment_entry)

	def delink_payment_entry(self, payment_entry):
		if payment_entry.payment_document == "Bank Transaction":
			self.update_linked_bank_transaction(payment_entry.payment_entry, allocated_amount=None)
		else:
			self.clear_linked_payment_entry(payment_entry, clearance_date=None)

	def clear_linked_payment_entry(self, payment_entry, clearance_date=None):
		doctype = payment_entry.payment_document
		docname = payment_entry.payment_entry

		# might be a bank transaction
		if doctype not in get_doctypes_for_bank_reconciliation():
			return

		if doctype == "Sales Invoice":
			frappe.db.set_value(
				"Sales Invoice Payment",
				dict(parenttype=doctype, parent=docname),
				"clearance_date",
				clearance_date,
			)
			return

		frappe.db.set_value(doctype, docname, "clearance_date", clearance_date)

	def update_linked_bank_transaction(self, bank_transaction_name, allocated_amount=None):
		"""For when a second bank transaction has fixed another, e.g. refund"""

		bt = frappe.get_doc(self.doctype, bank_transaction_name)
		if allocated_amount:
			bt.append(
				"payment_entries",
				{
					"payment_document": self.doctype,
					"payment_entry": self.name,
					"allocated_amount": allocated_amount,
				},
			)

		else:
			pe = next(
				(
					pe
					for pe in bt.payment_entries
					if pe.payment_document == self.doctype and pe.payment_entry == self.name
				),
				None,
			)
			if not pe:
				return

			bt.flags.updating_linked_bank_transaction = True
			bt.remove(pe)

		bt.save()

	def auto_set_party(self):
		from erpnext.accounts.doctype.bank_transaction.auto_match_party import AutoMatchParty

		if self.party_type and self.party:
			return

		result = None
		try:
			result = AutoMatchParty(
				bank_party_account_number=self.bank_party_account_number,
				bank_party_iban=self.bank_party_iban,
				bank_party_name=self.bank_party_name,
				description=self.description,
				deposit=self.deposit,
			).match()
		except Exception:
			frappe.log_error(title=_("Error in party matching for Bank Transaction {0}").format(self.name))

		if not result:
			return

		self.party_type, self.party = result


@frappe.whitelist()
def get_doctypes_for_bank_reconciliation():
	"""Get Bank Reconciliation doctypes from all the apps"""
	return frappe.get_hooks("bank_reconciliation_doctypes")


def get_clearance_details(transaction, payment_entry, bt_allocations, gl_entries, gl_bank_account):
	"""
	There should only be one bank gl entry for a voucher, except for JE.
	For JE, there can be multiple bank gl entries for the same account.
	In this case, the allocable_amount will be the sum of amounts of all gl entries of the account.
	There will be no gl entry for a Bank Transaction so return the unallocated amount.
	Should only clear the voucher if all bank gl entries are allocated.
	"""

	transaction_date = getdate(transaction.date)

	if payment_entry.payment_document == "Bank Transaction":
		bt = frappe.db.get_value(
			"Bank Transaction",
			payment_entry.payment_entry,
			("unallocated_amount", "bank_account"),
			as_dict=True,
		)

		if bt.bank_account != gl_bank_account:
			frappe.throw(
				_("Bank Account {} in Bank Transaction {} is not matching with Bank Account {}").format(
					bt.bank_account, payment_entry.payment_entry, gl_bank_account
				)
			)

		return abs(bt.unallocated_amount), True, transaction_date

	if gl_bank_account not in gl_entries:
		frappe.throw(
			_("{} {} is not affecting bank account {}").format(
				payment_entry.payment_document, payment_entry.payment_entry, gl_bank_account
			)
		)

	allocable_amount = gl_entries.pop(gl_bank_account) or 0
	if allocable_amount <= 0.0:
		frappe.throw(
			_("Invalid amount in accounting entries of {} {} for Account {}: {}").format(
				payment_entry.payment_document, payment_entry.payment_entry, gl_bank_account, allocable_amount
			)
		)

	matching_bt_allocaion = bt_allocations.pop(gl_bank_account, {})

	allocable_amount = flt(
		allocable_amount - matching_bt_allocaion.get("total", 0), transaction.precision("unallocated_amount")
	)

	should_clear = all(
		gl_entries[gle_account] == bt_allocations.get(gle_account, {}).get("total", 0)
		for gle_account in gl_entries
	)

	bt_allocation_date = matching_bt_allocaion.get("latest_date", None)
	clearance_date = transaction_date if not bt_allocation_date else max(transaction_date, bt_allocation_date)

	return allocable_amount, should_clear, clearance_date


def get_related_bank_gl_entries(docs):
	# nosemgrep: frappe-semgrep-rules.rules.frappe-using-db-sql
	if not docs:
		return {}

	result = frappe.db.sql(
		"""
        SELECT
            gle.voucher_type AS doctype,
            gle.voucher_no AS docname,
            gle.account AS gl_account,
            SUM(ABS(gle.credit_in_account_currency - gle.debit_in_account_currency)) AS amount
        FROM
            `tabGL Entry` gle
        LEFT JOIN
            `tabAccount` ac ON ac.name = gle.account
        WHERE
            ac.account_type = 'Bank'
            AND (gle.voucher_type, gle.voucher_no) IN %(docs)s
            AND gle.is_cancelled = 0
        GROUP BY
            gle.voucher_type, gle.voucher_no, gle.account
        """,
		{"docs": docs},
		as_dict=True,
	)

	entries = {}
	for row in result:
		key = (row["doctype"], row["docname"])
		if key not in entries:
			entries[key] = {}
		entries[key][row["gl_account"]] = row["amount"]

	return entries


def get_total_allocated_amount(docs):
	"""
	Gets the sum of allocations for a voucher on each bank GL account
	along with the latest bank transaction date
	NOTE: query may also include just saved vouchers/payments but with zero allocated_amount
	"""
	if not docs:
		return {}

	# nosemgrep: frappe-semgrep-rules.rules.frappe-using-db-sql
	result = frappe.db.sql(
		"""
		SELECT total, latest_date, gl_account, payment_document, payment_entry FROM (
			SELECT
				ROW_NUMBER() OVER w AS rownum,
				SUM(btp.allocated_amount) OVER(PARTITION BY ba.account, btp.payment_document, btp.payment_entry) AS total,
				FIRST_VALUE(bt.date) OVER w AS latest_date,
				ba.account AS gl_account,
				btp.payment_document,
				btp.payment_entry
			FROM
				`tabBank Transaction Payments` btp
			LEFT JOIN `tabBank Transaction` bt ON bt.name=btp.parent
			LEFT JOIN `tabBank Account` ba ON ba.name=bt.bank_account
			WHERE
				(btp.payment_document, btp.payment_entry) IN %(docs)s
				AND bt.docstatus = 1
			WINDOW w AS (PARTITION BY ba.account, btp.payment_document, btp.payment_entry ORDER BY bt.date DESC)
		) temp
		WHERE
			rownum = 1
		""",
		dict(docs=docs),
		as_dict=True,
	)

	payment_allocation_details = {}
	for row in result:
		row["latest_date"] = getdate(row["latest_date"])
		payment_allocation_details.setdefault((row["payment_document"], row["payment_entry"]), {})[
			row["gl_account"]
		] = row

	return payment_allocation_details


def get_reconciled_bank_transactions(doctype, docname):
	return frappe.get_all(
		"Bank Transaction Payments",
		filters={"payment_document": doctype, "payment_entry": docname},
		pluck="parent",
	)


def remove_from_bank_transaction(doctype, docname):
	"""Remove a (cancelled) voucher from all Bank Transactions."""
	for bt_name in get_reconciled_bank_transactions(doctype, docname):
		bt = frappe.get_doc("Bank Transaction", bt_name)
		if bt.docstatus == DocStatus.cancelled():
			continue

		modified = False

		for pe in bt.payment_entries:
			if pe.payment_document == doctype and pe.payment_entry == docname:
				bt.remove(pe)
				modified = True

		if modified:
			bt.save()
