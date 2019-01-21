# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext, json
from frappe import _, scrub, ValidationError
from frappe.utils import flt, comma_or, nowdate, getdate
from erpnext.accounts.utils import get_outstanding_invoices, get_account_currency, get_balance_on, get_balance_on_voucher
from erpnext.accounts.party import get_party_account
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account, \
	get_average_party_exchange_rate_on_journal_entry
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.hr.doctype.expense_claim.expense_claim import update_reimbursed_amount
from erpnext.controllers.accounts_controller import AccountsController, get_supplier_block_status

from six import string_types, iteritems

class InvalidPaymentEntry(ValidationError):
	pass


class PaymentEntry(AccountsController):
	def __init__(self, *args, **kwargs):
		super(PaymentEntry, self).__init__(*args, **kwargs)
		if not self.is_new():
			self.setup_party_account_field()

	def setup_party_account_field(self):
		self.party_account_field = None
		self.party_account = None
		self.party_account_currency = None

		if self.payment_type == "Receive":
			self.party_account_field = "paid_from"
			self.party_account = self.paid_from
			self.party_account_currency = self.paid_from_account_currency

		elif self.payment_type == "Pay":
			self.party_account_field = "paid_to"
			self.party_account = self.paid_to
			self.party_account_currency = self.paid_to_account_currency

	def validate(self):
		self.setup_party_account_field()
		self.set_missing_values()
		self.validate_payment_type()
		self.validate_party_details()
		self.validate_bank_accounts()
		self.set_exchange_rate()
		self.validate_mandatory()
		self.validate_reference_documents()
		self.set_amounts()
		self.clear_unallocated_reference_document_rows()
		self.validate_payment_against_negative_invoice()
		self.validate_transaction_reference()
		self.set_title()
		self.validate_duplicate_entry()
		self.validate_allocated_amount()
		self.ensure_supplier_is_not_blocked()

	def before_submit(self):
		self.update_reference_details()

	def on_submit(self):
		self.set_remarks()
		self.setup_party_account_field()
		if self.difference_amount:
			frappe.throw(_("Difference Amount must be zero"))
		self.make_gl_entries()
		self.update_advance_paid()
		self.update_expense_claim()

	def on_cancel(self):
		self.setup_party_account_field()
		self.make_gl_entries(cancel=1)
		self.update_reference_details()
		self.update_advance_paid()
		self.update_expense_claim()
		self.delink_advance_entry_references()

	def validate_duplicate_entry(self):
		reference_names = []
		for d in self.get("references"):
			if (d.reference_doctype, d.reference_name) in reference_names:
				frappe.throw(_("Row #{0}: Duplicate entry in References {1} {2}")
					.format(d.idx, d.reference_doctype, d.reference_name))
			reference_names.append((d.reference_doctype, d.reference_name))

	def validate_allocated_amount(self):
		for d in self.get("references"):
			if flt(d.allocated_amount) > flt(d.outstanding_amount) \
					or (flt(d.outstanding_amount) < 0 and flt(d.allocated_amount) < flt(d.outstanding_amount)):
				frappe.throw(_("Row #{0}: Allocated Amount of {1} against {2} is greater than its Outstanding Amount {3}.")
					.format(d.idx, flt(d.allocated_amount), d.reference_name, flt(d.outstanding_amount)))

	def delink_advance_entry_references(self):
		for reference in self.references:
			if reference.reference_doctype in ("Sales Invoice", "Purchase Invoice", "Landed Cost Voucher"):
				doc = frappe.get_doc(reference.reference_doctype, reference.reference_name)
				doc.delink_advance_entries(self.name)

	def set_missing_values(self, for_validate=False):
		if self.payment_type == "Internal Transfer":
			for field in ("party", "party_balance", "total_allocated_amount",
				"base_total_allocated_amount", "unallocated_amount"):
					self.set(field, None)
			self.references = []
		else:
			if not self.party_type:
				frappe.throw(_("Party Type is mandatory"))

			if not self.party:
				frappe.throw(_("Party is mandatory"))

			_party_name = "title" if self.party_type in ["Letter of Credit", "Student"] else scrub(self.party_type) + "_name"
			self.party_name = frappe.db.get_value(self.party_type, self.party, _party_name)

		if self.party:
			if not self.party_balance:
				self.party_balance = get_balance_on(party_type=self.party_type,
					party=self.party, date=self.posting_date, company=self.company)

			if not self.party_account:
				party_account = get_party_account(self.party_type, self.party, self.company)
				self.set(self.party_account_field, party_account)
				self.party_account = party_account

		if self.paid_from and not (self.paid_from_account_currency or self.paid_from_account_balance):
			acc = get_account_details(self.paid_from, self.posting_date, self.cost_center)
			self.paid_from_account_currency = acc.account_currency
			self.paid_from_account_balance = acc.account_balance

		if self.paid_to and not (self.paid_to_account_currency or self.paid_to_account_balance):
			acc = get_account_details(self.paid_to, self.posting_date, self.cost_center)
			self.paid_to_account_currency = acc.account_currency
			self.paid_to_account_balance = acc.account_balance

		self.party_account_currency = self.paid_from_account_currency \
			if self.payment_type=="Receive" else self.paid_to_account_currency

		self.update_reference_details()

	def update_reference_details(self):
		for d in self.get("references"):
			if d.allocated_amount:
				ref_details = get_reference_details(d.reference_doctype, d.reference_name, self.party_account_currency,
					self.party_type, self.party, self.paid_from if self.payment_type == "Receive" else self.paid_to)

				for field, value in iteritems(ref_details):
					d.set(field, value)

	def validate_payment_type(self):
		if self.payment_type not in ("Receive", "Pay", "Internal Transfer"):
			frappe.throw(_("Payment Type must be one of Receive, Pay and Internal Transfer"))

	def validate_party_details(self):
		if self.party:
			if not frappe.db.exists(self.party_type, self.party):
				frappe.throw(_("Invalid {0}: {1}").format(self.party_type, self.party))

			if self.party_account:
				self.validate_account_type(self.party_account,
					[erpnext.get_party_account_type(self.party_type)])

	def validate_bank_accounts(self):
		if self.payment_type in ("Pay", "Internal Transfer"):
			self.validate_account_type(self.paid_from, ["Bank", "Cash"])

		if self.payment_type in ("Receive", "Internal Transfer"):
			self.validate_account_type(self.paid_to, ["Bank", "Cash"])

	def validate_account_type(self, account, account_types):
		account_type = frappe.db.get_value("Account", account, "account_type")
		if account_type not in account_types:
			frappe.throw(_("Account Type for {0} must be {1}").format(account, comma_or(account_types)))

	def set_exchange_rate(self):
		if self.paid_from and not self.source_exchange_rate:
			if self.paid_from_account_currency == self.company_currency:
				self.source_exchange_rate = 1
			else:
				self.source_exchange_rate = get_exchange_rate(self.paid_from_account_currency,
					self.company_currency, self.posting_date)

		if self.paid_to and not self.target_exchange_rate:
			self.target_exchange_rate = get_exchange_rate(self.paid_to_account_currency,
				self.company_currency, self.posting_date)

	def validate_mandatory(self):
		for field in ("paid_amount", "received_amount", "source_exchange_rate", "target_exchange_rate"):
			if not self.get(field):
				frappe.throw(_("{0} is mandatory").format(self.meta.get_label(field)))

	def validate_reference_documents(self):
		if self.party_type == "Student":
			valid_reference_doctypes = ("Fees")
		elif self.party_type == "Customer":
			valid_reference_doctypes = ("Sales Order", "Sales Invoice", "Journal Entry")
		elif self.party_type == "Supplier":
			valid_reference_doctypes = ("Purchase Order", "Purchase Invoice", "Landed Cost Voucher", "Journal Entry")
		elif self.party_type == "Employee":
			valid_reference_doctypes = ("Expense Claim", "Journal Entry", "Employee Advance")
		elif self.party_type == "Letter of Credit":
			valid_reference_doctypes = ("Purchase Invoice", "Landed Cost Voucher", "Journal Entry")

		for d in self.get("references"):
			if not d.allocated_amount:
				continue
			if d.reference_doctype not in valid_reference_doctypes:
				frappe.throw(_("Reference Doctype must be one of {0}")
					.format(comma_or(valid_reference_doctypes)))

			elif d.reference_name:
				if not frappe.db.exists(d.reference_doctype, d.reference_name):
					frappe.throw(_("{0} {1} does not exist").format(d.reference_doctype, d.reference_name))
				else:
					ref_doc = frappe.get_doc(d.reference_doctype, d.reference_name)

					if d.reference_doctype != "Journal Entry":
						if self.party != ref_doc.get(scrub(self.party_type)):
							frappe.throw(_("{0} {1} is not associated with {2} {3}")
								.format(d.reference_doctype, d.reference_name, self.party_type, self.party))
					else:
						self.validate_journal_entry(d)

					if d.reference_doctype in ("Sales Invoice", "Purchase Invoice", "Landed Cost Voucher", "Expense Claim", "Fees"):
						if self.party_type == "Customer":
							ref_party_account = ref_doc.debit_to
						elif self.party_type == "Student":
							ref_party_account = ref_doc.receivable_account
						elif self.party_type in ["Supplier", "Letter of Credit"]:
							ref_party_account = ref_doc.credit_to
						elif self.party_type=="Employee":
							ref_party_account = ref_doc.payable_account

						if ref_party_account != self.party_account:
								frappe.throw(_("{0} {1} is associated with {2}, but Party Account is {3}")
									.format(d.reference_doctype, d.reference_name, ref_party_account, self.party_account))

					if ref_doc.docstatus != 1:
						frappe.throw(_("{0} {1} must be submitted")
							.format(d.reference_doctype, d.reference_name))

	def validate_journal_entry(self, d):
		je_accounts = frappe.db.sql("""select debit, credit from `tabJournal Entry Account`
			where account = %s and party_type=%s and party=%s and parent = %s and docstatus = 1
			and (reference_type is null or reference_type in ("", "Sales Order", "Purchase Order"))
			""", (self.party_account, self.party_type, self.party, d.reference_name), as_dict=True)

		if not je_accounts:
			frappe.throw(_("Row #{0}: Journal Entry {1} does not have account {2} or is already matched against a voucher")
				.format(d.idx, d.reference_name, self.party_account))
		else:
			dr_or_cr = "debit" if self.payment_type == "Receive" else "credit"
			valid = False
			for jvd in je_accounts:
				if flt(jvd[dr_or_cr]) > 0:
					valid = True
			if not valid:
				frappe.throw(_("Against Journal Entry {0} does not have any unmatched {1} entry")
					.format(d.reference_name, dr_or_cr))

	def set_amounts(self):
		self.set_amounts_in_company_currency()
		self.set_total_allocated_amount()
		self.set_unallocated_amount()
		self.set_difference_amount()

	def set_amounts_in_company_currency(self):
		self.base_paid_amount, self.base_received_amount, self.difference_amount = 0, 0, 0
		if self.paid_amount:
			self.base_paid_amount = flt(flt(self.paid_amount) * flt(self.source_exchange_rate),
				self.precision("base_paid_amount"))

		if self.received_amount:
			self.base_received_amount = flt(flt(self.received_amount) * flt(self.target_exchange_rate),
				self.precision("base_received_amount"))

	def set_total_allocated_amount(self):
		if self.payment_type == "Internal Transfer":
			return

		total_allocated_amount, base_total_allocated_amount = 0, 0
		for d in self.get("references"):
			if d.allocated_amount:
				total_allocated_amount += flt(d.allocated_amount)
				base_total_allocated_amount += flt(flt(d.allocated_amount) * flt(d.exchange_rate),
					self.precision("base_paid_amount"))

		self.total_allocated_amount = abs(total_allocated_amount)
		self.base_total_allocated_amount = abs(base_total_allocated_amount)

	def set_unallocated_amount(self):
		self.unallocated_amount = 0
		if self.party:
			total_deductions = sum([flt(d.amount) for d in self.get("deductions")])
			if self.payment_type == "Receive" \
				and self.base_total_allocated_amount < self.base_received_amount + total_deductions \
				and self.total_allocated_amount < self.paid_amount + (total_deductions / self.source_exchange_rate):
					self.unallocated_amount = (self.base_received_amount + total_deductions -
						self.base_total_allocated_amount) / self.source_exchange_rate
			elif self.payment_type == "Pay" \
				and self.base_total_allocated_amount < (self.base_paid_amount - total_deductions) \
				and self.total_allocated_amount < self.received_amount + (total_deductions / self.target_exchange_rate):
					self.unallocated_amount = (self.base_paid_amount - (total_deductions +
						self.base_total_allocated_amount)) / self.target_exchange_rate

	def set_difference_amount(self):
		base_unallocated_amount = flt(self.unallocated_amount) * (flt(self.source_exchange_rate)
			if self.payment_type == "Receive" else flt(self.target_exchange_rate))

		base_party_amount = flt(self.base_total_allocated_amount) + flt(base_unallocated_amount)

		if self.payment_type == "Receive":
			self.difference_amount = base_party_amount - self.base_received_amount
		elif self.payment_type == "Pay":
			self.difference_amount = self.base_paid_amount - base_party_amount
		else:
			self.difference_amount = self.base_paid_amount - flt(self.base_received_amount)

		total_deductions = sum([flt(d.amount) for d in self.get("deductions")])

		self.difference_amount = flt(self.difference_amount - total_deductions,
			self.precision("difference_amount"))

	# Paid amount is auto allocated in the reference document by default.
	# Clear the reference document which doesn't have allocated amount on validate so that form can be loaded fast
	def clear_unallocated_reference_document_rows(self):
		self.set("references", self.get("references", {"allocated_amount": ["not in", [0, None, ""]]}))
		frappe.db.sql("""delete from `tabPayment Entry Reference`
			where parent = %s and allocated_amount = 0""", self.name)

	def validate_payment_against_negative_invoice(self):
		if ((self.payment_type=="Pay" and self.party_type=="Customer")
				or (self.payment_type=="Receive" and self.party_type in ["Supplier", "Letter of Credit"])):

			total_negative_outstanding = sum([abs(flt(d.outstanding_amount))
				for d in self.get("references") if flt(d.outstanding_amount) < 0])

			paid_amount = self.paid_amount if self.payment_type=="Receive" else self.received_amount
			additional_charges = sum([flt(d.amount) for d in self.deductions])

			if not total_negative_outstanding:
				frappe.throw(_("Cannot {0} {1} {2} without any negative outstanding invoice")
					.format(self.payment_type, ("to" if self.party_type=="Customer" else "from"),
						self.party_type), InvalidPaymentEntry)

			elif paid_amount - additional_charges > total_negative_outstanding:
				frappe.throw(_("Paid Amount cannot be greater than total negative outstanding amount {0}")
					.format(total_negative_outstanding), InvalidPaymentEntry)

	def set_title(self):
		if self.payment_type in ("Receive", "Pay"):
			self.title = self.party
		else:
			self.title = self.paid_from + " - " + self.paid_to

	def validate_transaction_reference(self):
		bank_account = self.paid_to if self.payment_type == "Receive" else self.paid_from
		bank_account_type = frappe.db.get_value("Account", bank_account, "account_type")

		if bank_account_type == "Bank":
			if not self.reference_no or not self.reference_date:
				frappe.throw(_("Reference No and Reference Date is mandatory for Bank transaction"))

	def set_remarks(self):
		remarks = []

		if self.user_remark:
			remarks.append("Note: {0}".format(self.user_remark))

		if self.payment_type=="Internal Transfer":
			remarks.append(_("Amount {0} {1} transferred from {2} to {3}")
				.format(self.paid_from_account_currency, self.paid_amount, self.paid_from, self.paid_to))
		else:
			remarks.append(_("Amount {0} {1} {2} {3}").format(
				self.party_account_currency,
				self.paid_amount if self.payment_type=="Receive" else self.received_amount,
				_("received from") if self.payment_type=="Receive" else _("to"), self.party
			))

		if self.reference_no:
			remarks.append(_("Transaction reference no {0} dated {1}")
				.format(self.reference_no, self.reference_date))

		if self.payment_type in ["Receive", "Pay"]:
			for d in self.get("references"):
				if d.allocated_amount:
					remarks.append(_("Amount {0} {1} against {2} {3}").format(self.party_account_currency,
						d.allocated_amount, d.reference_doctype, d.reference_name))

		for d in self.get("deductions"):
			if d.amount:
				remarks.append(_("Amount {0} {1} deducted against {2}")
					.format(self.company_currency, d.amount, d.account))

		self.set("remarks", "\n".join(remarks))

	def make_gl_entries(self, cancel=0, adv_adj=0):
		if self.payment_type in ("Receive", "Pay") and not self.get("party_account_field"):
			self.setup_party_account_field()

		gl_entries = []
		self.add_party_gl_entries(gl_entries)
		self.add_bank_gl_entries(gl_entries)
		self.add_deductions_gl_entries(gl_entries)

		make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj)

	def add_party_gl_entries(self, gl_entries):
		if self.party_account:
			if self.payment_type=="Receive":
				against_account = self.paid_to
			else:
				against_account = self.paid_from

			party_gl_dict = self.get_gl_dict({
				"account": self.party_account,
				"party_type": self.party_type,
				"party": self.party,
				"against": against_account,
				"account_currency": self.party_account_currency,
				"cost_center": self.cost_center,
				"reference_no": self.reference_no,
				"reference_date": self.reference_date,
				"remarks": _("Note: {0}").format(self.user_remark) if self.user_remark else ""
			})

			dr_or_cr = "credit" if erpnext.get_party_account_type(self.party_type) == 'Receivable' else "debit"

			for d in self.get("references"):
				r = []
				if d.user_remark:
					r.append(d.user_remark)
				if self.user_remark:
					r.append(_("Note: {0}").format(self.user_remark))
				remarks = "\n".join(r)

				gle = party_gl_dict.copy()
				gle.update({
					"against_voucher_type": d.reference_doctype,
					"against_voucher": d.reference_name,
					"remarks": remarks
				})

				allocated_amount_in_company_currency = flt(flt(d.allocated_amount) * flt(d.exchange_rate),
					self.precision("paid_amount"))

				gle.update({
					dr_or_cr + "_in_account_currency": d.allocated_amount,
					dr_or_cr: allocated_amount_in_company_currency
				})

				gl_entries.append(gle)

			if self.unallocated_amount:
				base_unallocated_amount = base_unallocated_amount = self.unallocated_amount * \
					(self.source_exchange_rate if self.payment_type=="Receive" else self.target_exchange_rate)

				gle = party_gl_dict.copy()

				gle.update({
					dr_or_cr + "_in_account_currency": self.unallocated_amount,
					dr_or_cr: base_unallocated_amount
				})

				gl_entries.append(gle)

	def add_bank_gl_entries(self, gl_entries):
		if self.payment_type in ("Pay", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.paid_from,
					"account_currency": self.paid_from_account_currency,
					"against": self.party if self.payment_type=="Pay" else self.paid_to,
					"credit_in_account_currency": self.paid_amount,
					"credit": self.base_paid_amount,
					"cost_center": self.cost_center,
					"reference_no": self.reference_no,
					"reference_date": self.reference_date,
					"remarks": _("Note: {0}").format(self.user_remark) if self.user_remark else ""
				})
			)
		if self.payment_type in ("Receive", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.paid_to,
					"account_currency": self.paid_to_account_currency,
					"against": self.party if self.payment_type=="Receive" else self.paid_from,
					"debit_in_account_currency": self.received_amount,
					"debit": self.base_received_amount,
					"cost_center": self.cost_center,
					"reference_no": self.reference_no,
					"reference_date": self.reference_date,
					"remarks": _("Note: {0}").format(self.user_remark) if self.user_remark else ""
				})
			)

	def add_deductions_gl_entries(self, gl_entries):
		for d in self.get("deductions"):
			if d.amount:
				account_currency = get_account_currency(d.account)
				if account_currency != self.company_currency:
					frappe.throw(_("Currency for {0} must be {1}").format(d.account, self.company_currency))

				r = []
				if d.user_remark:
					r.append(d.user_remark)
				if self.user_remark:
					r.append(_("Note: {0}").format(self.user_remark))
				remarks = "\n".join(r)

				gl_entries.append(
					self.get_gl_dict({
						"account": d.account,
						"account_currency": account_currency,
						"against": self.party or self.paid_from,
						"debit_in_account_currency": d.amount,
						"debit": d.amount,
						"cost_center": d.cost_center,
						"reference_no": self.reference_no,
						"reference_date": self.reference_date,
						"remarks": remarks
					})
				)

	def update_advance_paid(self):
		if self.payment_type in ("Receive", "Pay") and self.party:
			for d in self.get("references"):
				if d.allocated_amount \
					and d.reference_doctype in ("Sales Order", "Purchase Order", "Employee Advance"):
						frappe.get_doc(d.reference_doctype, d.reference_name).set_total_advance_paid()

	def update_expense_claim(self):
		if self.payment_type in ("Pay") and self.party:
			for d in self.get("references"):
				if d.reference_doctype=="Expense Claim" and d.reference_name:
					doc = frappe.get_doc("Expense Claim", d.reference_name)
					update_reimbursed_amount(doc)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.reference_no = reference_doc.name
		self.reference_date = nowdate()

	def calculate_deductions(self, tax_details):
		return {
			"account": tax_details['tax']['account_head'],
			"cost_center": frappe.get_cached_value('Company',  self.company,  "cost_center"),
			"amount": self.total_allocated_amount * (tax_details['tax']['rate'] / 100)
		}

@frappe.whitelist()
def get_outstanding_reference_documents(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	# confirm that Supplier is not blocked
	if args.get('party_type') == 'Supplier':
		supplier_status = get_supplier_block_status(args['party'])
		if supplier_status['on_hold']:
			if supplier_status['hold_type'] == 'All':
				return []
			elif supplier_status['hold_type'] == 'Payments':
				if not supplier_status['release_date'] or getdate(nowdate()) <= supplier_status['release_date']:
					return []

	party_account_currency = get_account_currency(args.get("party_account"))
	company_currency = frappe.get_cached_value('Company',  args.get("company"),  "default_currency")

	# Get outstanding invoices
	condition = ""
	if args.get("voucher_type") and args.get("voucher_no"):
		condition = " and voucher_type='{0}' and voucher_no='{1}'"\
			.format(frappe.db.escape(args["voucher_type"]), frappe.db.escape(args["voucher_no"]))

	# Add cost center condition
	if args.get("cost_center"):
		condition += " and cost_center='%s'" % args.get("cost_center")

	negative_invoices = False
	party_account_type = erpnext.get_party_account_type(args.get("party_type"))
	if (args.get("payment_type") == "Receive" and party_account_type == "Payable") \
			or (args.get("payment_type") == "Payable" and party_account_type == "Receivable"):
		negative_invoices = True

	outstanding_invoices = get_outstanding_invoices(args.get("party_type"), args.get("party"),
		args.get("party_account"), condition=condition, negative_invoices=negative_invoices)

	for d in outstanding_invoices:
		d["exchange_rate"] = 1
		if party_account_currency != company_currency:
			if d.voucher_type in ("Sales Invoice", "Purchase Invoice", "Expense Claim"):
				d["exchange_rate"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "conversion_rate")
			elif d.voucher_type == "Journal Entry":
				d["exchange_rate"] = get_average_party_exchange_rate_on_journal_entry(d.voucher_no,
					args.get("party_type"), args.get("party"), args.get("party_account"))
		if d.voucher_type in ("Purchase Invoice"):
			d["bill_no"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "bill_no")

	# Get all SO / PO which are not fully billed or aginst which full advance not paid
	orders_to_be_billed = []
	if not negative_invoices:
		orders_to_be_billed = get_orders_to_be_billed(args.get("posting_date"),args.get("party_type"),
			args.get("party"), party_account_currency, company_currency)

	return outstanding_invoices + orders_to_be_billed


def get_orders_to_be_billed(posting_date, party_type, party, party_account_currency, company_currency, cost_center=None):
	if party_type == "Customer":
		voucher_type = 'Sales Order'
	elif party_type == "Supplier":
		voucher_type = 'Purchase Order'
	else:
		return []

	# Add cost center condition
	if voucher_type:
		doc = frappe.get_doc({"doctype": voucher_type})
		condition = ""
		if doc and hasattr(doc, 'cost_center'):
			condition = " and cost_center='%s'" % cost_center

	ref_field = "base_grand_total" if party_account_currency == company_currency else "grand_total"

	orders = frappe.db.sql("""
		select
			name as voucher_no,
			{ref_field} as invoice_amount,
			({ref_field} - advance_paid) as outstanding_amount,
			transaction_date as posting_date
		from
			`tab{voucher_type}`
		where
			{party_type} = %s
			and docstatus = 1
			and ifnull(status, "") != "Closed"
			and {ref_field} > advance_paid
			and abs(100 - per_billed) > 0.01
			{condition}
		order by
			transaction_date, name
	""".format(**{
		"ref_field": ref_field,
		"voucher_type": voucher_type,
		"party_type": scrub(party_type),
		"condition": condition
	}), party, as_dict=True)

	order_list = []
	for d in orders:
		d["voucher_type"] = voucher_type
		# This assumes that the exchange rate required is the one in the SO
		d["exchange_rate"] = get_exchange_rate(party_account_currency, company_currency, posting_date)
		order_list.append(d)

	return order_list

def get_negative_outstanding_invoices(party_type, party, party_account, party_account_currency, company_currency, cost_center=None):
	voucher_type = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
	supplier_condition = ""
	if voucher_type == "Purchase Invoice":
		supplier_condition = "and (release_date is null or release_date <= CURDATE())"
	if party_account_currency == company_currency:
		grand_total_field = "base_grand_total"
		rounded_total_field = "base_rounded_total"
	else:
		grand_total_field = "grand_total"
		rounded_total_field = "rounded_total"

	res = frappe.db.sql("""
		select
			"{voucher_type}" as voucher_type, name as voucher_no,
			if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) as invoice_amount,
			outstanding_amount, posting_date,
			due_date, conversion_rate as exchange_rate
		from
			`tab{voucher_type}`
		where
			{party_type} = %s and {party_account} = %s and docstatus = 1 and outstanding_amount < 0
			{supplier_condition}
		order by
			posting_date, name
		""".format(**{
			"supplier_condition": supplier_condition,
			"rounded_total_field": rounded_total_field,
			"grand_total_field": grand_total_field,
			"voucher_type": voucher_type,
			"party_type": scrub(party_type),
			"party_account": "debit_to" if party_type == "Customer" else "credit_to",
			"cost_center": cost_center
		}), (party, party_account), as_dict=True)

	return res


@frappe.whitelist()
def get_party_details(company, party_type, party, date, cost_center=None):
	if not frappe.db.exists(party_type, party):
		frappe.throw(_("Invalid {0}: {1}").format(party_type, party))

	party_account = get_party_account(party_type, party, company)

	account_currency = get_account_currency(party_account)
	account_balance = get_balance_on(party_account, date, cost_center=cost_center)
	_party_name = "title" if party_type in ["Student", "Letter of Credit"] else scrub(party_type) + "_name"
	party_name = frappe.db.get_value(party_type, party, _party_name)
	party_balance = get_balance_on(party_type=party_type, party=party, cost_center=cost_center)

	return {
		"party_account": party_account,
		"party_name": party_name,
		"party_account_currency": account_currency,
		"party_balance": party_balance,
		"account_balance": account_balance
	}


@frappe.whitelist()
def get_account_details(account, date, cost_center=None):
	frappe.has_permission('Payment Entry', throw=True)
	return frappe._dict({
		"account_currency": get_account_currency(account),
		"account_balance": get_balance_on(account, date, cost_center=cost_center),
		"account_type": frappe.db.get_value("Account", account, "account_type")
	})


@frappe.whitelist()
def get_company_defaults(company):
	fields = ["write_off_account", "exchange_gain_loss_account", "cost_center"]
	ret = frappe.get_cached_value('Company',  company,  fields, as_dict=1)

	for fieldname in fields:
		if not ret[fieldname]:
			frappe.throw(_("Please set default {0} in Company {1}")
				.format(frappe.get_meta("Company").get_label(fieldname), company))

	return ret


@frappe.whitelist()
def get_reference_details(reference_doctype, reference_name, party_account_currency, party_type, party, account):
	total_amount = outstanding_amount = None
	exchange_rate = 1

	ref_doc = frappe.get_doc(reference_doctype, reference_name)
	company_currency = ref_doc.get("company_currency") or erpnext.get_company_currency(ref_doc.company)

	if reference_doctype == "Fees":
		total_amount = ref_doc.get("grand_total")
		exchange_rate = 1
		outstanding_amount = ref_doc.get("outstanding_amount")
	elif reference_doctype == "Landed Cost Voucher":
		total_amount = ref_doc.get("total_taxes_and_charges")
		exchange_rate = 1
		outstanding_amount = ref_doc.get("outstanding_amount")
	elif reference_doctype == "Journal Entry" and ref_doc.docstatus == 1:
		total_amount = ref_doc.get("total_amount")
		if ref_doc.multi_currency:
			exchange_rate = get_average_party_exchange_rate_on_journal_entry(reference_name, party_type, party, account)
		else:
			exchange_rate = 1
		outstanding_amount = get_balance_on_voucher("Journal Entry", reference_name, party_type, party, account)
	elif reference_doctype != "Journal Entry":
		if party_account_currency == company_currency:
			if ref_doc.doctype == "Expense Claim":
				total_amount = ref_doc.total_sanctioned_amount
			elif ref_doc.doctype == "Employee Advance":
				total_amount = ref_doc.advance_amount
			else:
				total_amount = ref_doc.base_grand_total
			exchange_rate = 1
		else:
			total_amount = ref_doc.grand_total

			# Get the exchange rate from the original ref doc
			# or get it based on the posting date of the ref doc
			exchange_rate = ref_doc.get("conversion_rate") or \
				get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)

		if reference_doctype in ("Sales Invoice", "Purchase Invoice"):
			outstanding_amount = ref_doc.get("outstanding_amount")
		elif reference_doctype == "Expense Claim":
			outstanding_amount = flt(ref_doc.get("total_sanctioned_amount")) \
				- flt(ref_doc.get("total_amount+reimbursed")) - flt(ref_doc.get("total_advance_amount"))
		elif reference_doctype == "Employee Advance":
			outstanding_amount = ref_doc.advance_amount - flt(ref_doc.paid_amount)
		else:
			outstanding_amount = flt(total_amount) - flt(ref_doc.advance_paid)
	else:
		# Get the exchange rate based on the posting date of the ref doc
		exchange_rate = get_exchange_rate(party_account_currency,
			company_currency, ref_doc.posting_date)

	return frappe._dict({
		"due_date": ref_doc.get("due_date"),
		"total_amount": total_amount,
		"outstanding_amount": outstanding_amount,
		"exchange_rate": exchange_rate
	})


@frappe.whitelist()
def get_payment_entry(dt, dn, party_amount=None, bank_account=None, bank_amount=None):
	doc = frappe.get_doc(dt, dn)
	if dt in ("Sales Order", "Purchase Order") and flt(doc.per_billed, 2) > 0:
		frappe.throw(_("Can only make payment against unbilled {0}").format(dt))

	if dt in ("Sales Invoice", "Sales Order"):
		party_type = "Customer"
	elif dt == "Purchase Order":
		party_type = "Supplier"
	elif dt == "Purchase Invoice":
		party_type = "Letter of Credit" if doc.letter_of_credit else "Supplier"
	elif dt == "Landed Cost Voucher":
		party_type = doc.party_type
	elif dt in ("Expense Claim", "Employee Advance"):
		party_type = "Employee"
	elif dt in ("Fees"):
		party_type = "Student"

	# party account
	if dt == "Sales Invoice":
		party_account = doc.debit_to
	elif dt in ["Purchase Invoice", "Landed Cost Voucher"]:
		party_account = doc.credit_to
	elif dt == "Fees":
		party_account = doc.receivable_account
	elif dt == "Employee Advance":
		party_account = doc.advance_account
	elif dt == "Expense Claim":
		party_account = doc.payable_account
	else:
		party_account = get_party_account(party_type, doc.get(scrub(party_type)), doc.company)

	party_account_currency = doc.get("party_account_currency") or get_account_currency(party_account)

	# payment type
	if (dt == "Sales Order" or (dt in ("Sales Invoice", "Fees") and doc.outstanding_amount > 0)) \
		or (dt=="Purchase Invoice" and doc.outstanding_amount < 0):
			payment_type = "Receive"
	else:
		payment_type = "Pay"

	# amounts
	grand_total = outstanding_amount = 0
	if party_amount:
		grand_total = outstanding_amount = party_amount
	elif dt in ("Sales Invoice", "Purchase Invoice"):
		if party_account_currency == doc.company_currency:
			grand_total = doc.base_rounded_total or doc.base_grand_total
		else:
			grand_total = doc.rounded_total or doc.grand_total
		outstanding_amount = doc.outstanding_amount
	elif dt in ("Expense Claim"):
		grand_total = doc.total_sanctioned_amount
		outstanding_amount = doc.total_sanctioned_amount \
			- doc.total_amount_reimbursed - flt(doc.total_advance_amount)
	elif dt == "Employee Advance":
		grand_total = doc.advance_amount
		outstanding_amount = flt(doc.advance_amount) - flt(doc.paid_amount)
	elif dt == "Fees":
		grand_total = doc.grand_total
		outstanding_amount = doc.outstanding_amount
	elif dt == "Landed Cost Voucher":
		grand_total = doc.total_taxes_and_charges
		outstanding_amount = doc.outstanding_amount
	else:
		if party_account_currency == doc.company_currency:
			grand_total = flt(doc.get("base_rounded_total") or doc.base_grand_total)
		else:
			grand_total = flt(doc.get("rounded_total") or doc.grand_total)
		outstanding_amount = grand_total - flt(doc.advance_paid)

	# bank or cash
	bank = get_default_bank_cash_account(doc.company, "Bank", mode_of_payment=doc.get("mode_of_payment"),
		account=bank_account)

	paid_amount = received_amount = 0
	if party_account_currency == bank.account_currency:
		paid_amount = received_amount = abs(outstanding_amount)
	elif payment_type == "Receive":
		paid_amount = abs(outstanding_amount)
		if bank_amount:
			received_amount = bank_amount
	else:
		received_amount = abs(outstanding_amount)
		if bank_amount:
			paid_amount = bank_amount

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = payment_type
	pe.company = doc.company
	pe.cost_center = doc.get("cost_center")
	pe.posting_date = nowdate()
	pe.mode_of_payment = doc.get("mode_of_payment")
	pe.party_type = party_type
	pe.party = doc.get(scrub(party_type)) or doc.get("party")
	pe.contact_person = doc.get("contact_person")
	pe.contact_email = doc.get("contact_email")
	pe.ensure_supplier_is_not_blocked()

	pe.paid_from = party_account if payment_type=="Receive" else bank.account
	pe.paid_to = party_account if payment_type=="Pay" else bank.account
	pe.paid_from_account_currency = party_account_currency \
		if payment_type=="Receive" else bank.account_currency
	pe.paid_to_account_currency = party_account_currency if payment_type=="Pay" else bank.account_currency
	pe.paid_amount = paid_amount
	pe.received_amount = received_amount
	pe.allocate_payment_amount = 1
	pe.letter_head = doc.get("letter_head")

	# only Purchase Invoice can be blocked individually
	if doc.doctype == "Purchase Invoice" and doc.invoice_is_blocked():
		frappe.msgprint(_('{0} is on hold till {1}'.format(doc.name, doc.release_date)))
	else:
		pe.append("references", {
			'reference_doctype': dt,
			'reference_name': dn,
			"bill_no": doc.get("bill_no"),
			"due_date": doc.get("due_date"),
			'total_amount': grand_total,
			'outstanding_amount': outstanding_amount,
			'allocated_amount': outstanding_amount
		})

	pe.setup_party_account_field()
	pe.set_missing_values()
	if party_account and bank:
		pe.set_exchange_rate()
		pe.set_amounts()
	return pe


def get_paid_amount(dt, dn, party_type, party, account, due_date):
	if party_type=="Customer":
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	paid_amount = frappe.db.sql("""
		select ifnull(sum({dr_or_cr}), 0) as paid_amount
		from `tabGL Entry`
		where against_voucher_type = %s
			and against_voucher = %s
			and party_type = %s
			and party = %s
			and account = %s
			and due_date = %s
			and {dr_or_cr} > 0
	""".format(dr_or_cr=dr_or_cr), (dt, dn, party_type, party, account, due_date))

	return paid_amount[0][0] if paid_amount else 0

@frappe.whitelist()
def get_party_and_account_balance(company, date, paid_from=None, paid_to=None, ptype=None, pty=None, cost_center=None):
	return frappe._dict({
		"party_balance": get_balance_on(party_type=ptype, party=pty, cost_center=cost_center),
		"paid_from_account_balance": get_balance_on(paid_from, date, cost_center=cost_center),
		"paid_to_account_balance": get_balance_on(paid_to, date=date, cost_center=cost_center)
	})
