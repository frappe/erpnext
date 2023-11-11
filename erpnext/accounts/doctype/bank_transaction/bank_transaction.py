# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from erpnext.controllers.status_updater import StatusUpdater


class BankTransaction(StatusUpdater):
	def after_insert(self):
		self.unallocated_amount = abs(flt(self.withdrawal) - flt(self.deposit))

	def on_submit(self):
		self.clear_linked_payment_entries()
		self.set_status()

		if frappe.db.get_single_value("Accounts Settings", "enable_party_matching"):
			self.auto_set_party()

	_saving_flag = False

	# nosemgrep: frappe-semgrep-rules.rules.frappe-modifying-but-not-comitting
	def on_update_after_submit(self):
		"Run on save(). Avoid recursion caused by multiple saves"
		if not self._saving_flag:
			self._saving_flag = True
			self.clear_linked_payment_entries()
			self.update_allocations()
			self._saving_flag = False

	def on_cancel(self):
		self.clear_linked_payment_entries(for_cancel=True)
		self.set_status(update=True)

	def update_allocations(self):
		"The doctype does not allow modifications after submission, so write to the db direct"
		if self.payment_entries:
			allocated_amount = sum(p.allocated_amount for p in self.payment_entries)
		else:
			allocated_amount = 0.0

		amount = abs(flt(self.withdrawal) - flt(self.deposit))
		self.db_set("allocated_amount", flt(allocated_amount))
		self.db_set("unallocated_amount", amount - flt(allocated_amount))
		self.reload()
		self.set_status(update=True)

	def add_payment_entries(self, vouchers):
		"Add the vouchers with zero allocation. Save() will perform the allocations and clearance"
		if 0.0 >= self.unallocated_amount:
			frappe.throw(frappe._("Bank Transaction {0} is already fully reconciled").format(self.name))

		added = False
		for voucher in vouchers:
			# Can't add same voucher twice
			found = False
			for pe in self.payment_entries:
				if (
					pe.payment_document == voucher["payment_doctype"]
					and pe.payment_entry == voucher["payment_name"]
				):
					found = True

			if not found:
				pe = {
					"payment_document": voucher["payment_doctype"],
					"payment_entry": voucher["payment_name"],
					"allocated_amount": 0.0,  # Temporary
				}
				child = self.append("payment_entries", pe)
				added = True

		# runs on_update_after_submit
		if added:
			self.save()

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
		remaining_amount = self.unallocated_amount
		for payment_entry in self.payment_entries:
			if payment_entry.allocated_amount == 0.0:
				unallocated_amount, should_clear, latest_transaction = get_clearance_details(
					self, payment_entry
				)

				if 0.0 == unallocated_amount:
					if should_clear:
						latest_transaction.clear_linked_payment_entry(payment_entry)
					self.db_delete_payment_entry(payment_entry)

				elif remaining_amount <= 0.0:
					self.db_delete_payment_entry(payment_entry)

				elif 0.0 < unallocated_amount and unallocated_amount <= remaining_amount:
					payment_entry.db_set("allocated_amount", unallocated_amount)
					remaining_amount -= unallocated_amount
					if should_clear:
						latest_transaction.clear_linked_payment_entry(payment_entry)

				elif 0.0 < unallocated_amount and unallocated_amount > remaining_amount:
					payment_entry.db_set("allocated_amount", remaining_amount)
					remaining_amount = 0.0

				elif 0.0 > unallocated_amount:
					self.db_delete_payment_entry(payment_entry)
					frappe.throw(frappe._("Voucher {0} is over-allocated by {1}").format(unallocated_amount))

		self.reload()

	def db_delete_payment_entry(self, payment_entry):
		frappe.db.delete("Bank Transaction Payments", {"name": payment_entry.name})

	@frappe.whitelist()
	def remove_payment_entries(self):
		for payment_entry in self.payment_entries:
			self.remove_payment_entry(payment_entry)
		# runs on_update_after_submit
		self.save()

	def remove_payment_entry(self, payment_entry):
		"Clear payment entry and clearance"
		self.clear_linked_payment_entry(payment_entry, for_cancel=True)
		self.remove(payment_entry)

	def clear_linked_payment_entries(self, for_cancel=False):
		if for_cancel:
			for payment_entry in self.payment_entries:
				self.clear_linked_payment_entry(payment_entry, for_cancel)
		else:
			self.allocate_payment_entries()

	def clear_linked_payment_entry(self, payment_entry, for_cancel=False):
		clearance_date = None if for_cancel else self.date
		set_voucher_clearance(
			payment_entry.payment_document, payment_entry.payment_entry, clearance_date, self
		)

	def auto_set_party(self):
		from erpnext.accounts.doctype.bank_transaction.auto_match_party import AutoMatchParty

		if self.party_type and self.party:
			return

		result = AutoMatchParty(
			bank_party_account_number=self.bank_party_account_number,
			bank_party_iban=self.bank_party_iban,
			bank_party_name=self.bank_party_name,
			description=self.description,
			deposit=self.deposit,
		).match()

		if result:
			party_type, party = result
			frappe.db.set_value(
				"Bank Transaction", self.name, field={"party_type": party_type, "party": party}
			)


@frappe.whitelist()
def get_doctypes_for_bank_reconciliation():
	"""Get Bank Reconciliation doctypes from all the apps"""
	return frappe.get_hooks("bank_reconciliation_doctypes")


def get_clearance_details(transaction, payment_entry):
	"""
	There should only be one bank gle for a voucher.
	Could be none for a Bank Transaction.
	But if a JE, could affect two banks.
	Should only clear the voucher if all bank gles are allocated.
	"""
	gl_bank_account = frappe.db.get_value("Bank Account", transaction.bank_account, "account")
	gles = get_related_bank_gl_entries(payment_entry.payment_document, payment_entry.payment_entry)
	bt_allocations = get_total_allocated_amount(
		payment_entry.payment_document, payment_entry.payment_entry
	)

	unallocated_amount = min(
		transaction.unallocated_amount,
		get_paid_amount(payment_entry, transaction.currency, gl_bank_account),
	)
	unmatched_gles = len(gles)
	latest_transaction = transaction
	for gle in gles:
		if gle["gl_account"] == gl_bank_account:
			if gle["amount"] <= 0.0:
				frappe.throw(
					frappe._("Voucher {0} value is broken: {1}").format(
						payment_entry.payment_entry, gle["amount"]
					)
				)

			unmatched_gles -= 1
			unallocated_amount = gle["amount"]
			for a in bt_allocations:
				if a["gl_account"] == gle["gl_account"]:
					unallocated_amount = gle["amount"] - a["total"]
					if frappe.utils.getdate(transaction.date) < a["latest_date"]:
						latest_transaction = frappe.get_doc("Bank Transaction", a["latest_name"])
		else:
			# Must be a Journal Entry affecting more than one bank
			for a in bt_allocations:
				if a["gl_account"] == gle["gl_account"] and a["total"] == gle["amount"]:
					unmatched_gles -= 1

	return unallocated_amount, unmatched_gles == 0, latest_transaction


def get_related_bank_gl_entries(doctype, docname):
	# nosemgrep: frappe-semgrep-rules.rules.frappe-using-db-sql
	result = frappe.db.sql(
		"""
		SELECT
			ABS(gle.credit_in_account_currency - gle.debit_in_account_currency) AS amount,
			gle.account AS gl_account
		FROM
			`tabGL Entry` gle
		LEFT JOIN
			`tabAccount` ac ON ac.name=gle.account
		WHERE
			ac.account_type = 'Bank'
			AND gle.voucher_type = %(doctype)s
			AND gle.voucher_no = %(docname)s
			AND is_cancelled = 0
		""",
		dict(doctype=doctype, docname=docname),
		as_dict=True,
	)
	return result


def get_total_allocated_amount(doctype, docname):
	"""
	Gets the sum of allocations for a voucher on each bank GL account
	along with the latest bank transaction name & date
	NOTE: query may also include just saved vouchers/payments but with zero allocated_amount
	"""
	# nosemgrep: frappe-semgrep-rules.rules.frappe-using-db-sql
	result = frappe.db.sql(
		"""
		SELECT total, latest_name, latest_date, gl_account FROM (
			SELECT
				ROW_NUMBER() OVER w AS rownum,
				SUM(btp.allocated_amount) OVER(PARTITION BY ba.account) AS total,
				FIRST_VALUE(bt.name) OVER w AS latest_name,
				FIRST_VALUE(bt.date) OVER w AS latest_date,
				ba.account AS gl_account
			FROM
				`tabBank Transaction Payments` btp
			LEFT JOIN `tabBank Transaction` bt ON bt.name=btp.parent
			LEFT JOIN `tabBank Account` ba ON ba.name=bt.bank_account
			WHERE
				btp.payment_document = %(doctype)s
				AND btp.payment_entry = %(docname)s
				AND bt.docstatus = 1
			WINDOW w AS (PARTITION BY ba.account ORDER BY bt.date desc)
		) temp
		WHERE
			rownum = 1
		""",
		dict(doctype=doctype, docname=docname),
		as_dict=True,
	)
	for row in result:
		# Why is this *sometimes* a byte string?
		if isinstance(row["latest_name"], bytes):
			row["latest_name"] = row["latest_name"].decode()
		row["latest_date"] = frappe.utils.getdate(row["latest_date"])
	return result


def get_paid_amount(payment_entry, currency, gl_bank_account):
	if payment_entry.payment_document in ["Payment Entry", "Sales Invoice", "Purchase Invoice"]:

		paid_amount_field = "paid_amount"
		if payment_entry.payment_document == "Payment Entry":
			doc = frappe.get_doc("Payment Entry", payment_entry.payment_entry)

			if doc.payment_type == "Receive":
				paid_amount_field = (
					"received_amount" if doc.paid_to_account_currency == currency else "base_received_amount"
				)
			elif doc.payment_type == "Pay":
				paid_amount_field = (
					"paid_amount" if doc.paid_from_account_currency == currency else "base_paid_amount"
				)

		return frappe.db.get_value(
			payment_entry.payment_document, payment_entry.payment_entry, paid_amount_field
		)

	elif payment_entry.payment_document == "Journal Entry":
		return abs(
			frappe.db.get_value(
				"Journal Entry Account",
				{"parent": payment_entry.payment_entry, "account": gl_bank_account},
				"sum(debit_in_account_currency-credit_in_account_currency)",
			)
			or 0
		)

	elif payment_entry.payment_document == "Expense Claim":
		return frappe.db.get_value(
			payment_entry.payment_document, payment_entry.payment_entry, "total_amount_reimbursed"
		)

	elif payment_entry.payment_document == "Loan Disbursement":
		return frappe.db.get_value(
			payment_entry.payment_document, payment_entry.payment_entry, "disbursed_amount"
		)

	elif payment_entry.payment_document == "Loan Repayment":
		return frappe.db.get_value(
			payment_entry.payment_document, payment_entry.payment_entry, "amount_paid"
		)

	elif payment_entry.payment_document == "Bank Transaction":
		dep, wth = frappe.db.get_value(
			"Bank Transaction", payment_entry.payment_entry, ("deposit", "withdrawal")
		)
		return abs(flt(wth) - flt(dep))

	else:
		frappe.throw(
			"Please reconcile {0}: {1} manually".format(
				payment_entry.payment_document, payment_entry.payment_entry
			)
		)


def set_voucher_clearance(doctype, docname, clearance_date, self):
	if doctype in get_doctypes_for_bank_reconciliation():
		if (
			doctype == "Payment Entry"
			and frappe.db.get_value("Payment Entry", docname, "payment_type") == "Internal Transfer"
			and len(get_reconciled_bank_transactions(doctype, docname)) < 2
		):
			return
		frappe.db.set_value(doctype, docname, "clearance_date", clearance_date)

	elif doctype == "Sales Invoice":
		frappe.db.set_value(
			"Sales Invoice Payment",
			dict(parenttype=doctype, parent=docname),
			"clearance_date",
			clearance_date,
		)

	elif doctype == "Bank Transaction":
		# For when a second bank transaction has fixed another, e.g. refund
		bt = frappe.get_doc(doctype, docname)
		if clearance_date:
			vouchers = [{"payment_doctype": "Bank Transaction", "payment_name": self.name}]
			bt.add_payment_entries(vouchers)
		else:
			for pe in bt.payment_entries:
				if pe.payment_document == self.doctype and pe.payment_entry == self.name:
					bt.remove(pe)
					bt.save()
					break


def get_reconciled_bank_transactions(doctype, docname):
	return frappe.get_all(
		"Bank Transaction Payments",
		filters={"payment_document": doctype, "payment_entry": docname},
		pluck="parent",
	)


@frappe.whitelist()
def unclear_reference_payment(doctype, docname, bt_name):
	bt = frappe.get_doc("Bank Transaction", bt_name)
	set_voucher_clearance(doctype, docname, None, bt)
	return docname
