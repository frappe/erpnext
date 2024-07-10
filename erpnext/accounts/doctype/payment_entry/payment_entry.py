# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
from functools import reduce

import frappe
from frappe import ValidationError, _, qb, scrub, throw
from frappe.utils import cint, comma_or, flt, getdate, nowdate
from frappe.utils.data import comma_and, fmt_money
from pypika import Case
from pypika.functions import Coalesce, Sum

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.doctype.bank_account.bank_account import (
	get_bank_account_details,
	get_default_company_bank_account,
	get_party_bank_account,
)
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import (
	get_party_account_based_on_invoice_discounting,
)
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from erpnext.accounts.general_ledger import (
	make_gl_entries,
	make_reverse_gl_entries,
	process_gl_map,
)
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import (
	cancel_exchange_gain_loss_journal,
	get_account_currency,
	get_balance_on,
	get_outstanding_invoices,
	get_party_types_from_account_type,
)
from erpnext.controllers.accounts_controller import (
	AccountsController,
	get_supplier_block_status,
	validate_taxes_and_charges,
)
from erpnext.setup.utils import get_exchange_rate


class InvalidPaymentEntry(ValidationError):
	pass


class PaymentEntry(AccountsController):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
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
		self.set_liability_account()
		self.set_missing_ref_details(force=True)
		self.validate_payment_type()
		self.validate_party_details()
		self.set_exchange_rate()
		self.validate_mandatory()
		self.validate_reference_documents()
		self.set_amounts()
		self.validate_amounts()
		self.apply_taxes()
		self.set_amounts_after_tax()
		self.clear_unallocated_reference_document_rows()
		self.validate_transaction_reference()
		self.set_title()
		self.set_remarks()
		self.validate_duplicate_entry()
		self.validate_payment_type_with_outstanding()
		self.validate_allocated_amount()
		self.validate_paid_invoices()
		self.ensure_supplier_is_not_blocked()
		self.set_tax_withholding()
		self.set_status()
		self.set_total_in_words()

	def on_submit(self):
		if self.difference_amount:
			frappe.throw(_("Difference Amount must be zero"))
		self.make_gl_entries()
		self.update_outstanding_amounts()
		self.update_advance_paid()
		self.update_payment_schedule()
		self.set_status()

	def set_liability_account(self):
		# Auto setting liability account should only be done during 'draft' status
		if self.docstatus > 0 or self.payment_type == "Internal Transfer":
			return

		self.book_advance_payments_in_separate_party_account = False
		if self.party_type not in ("Customer", "Supplier"):
			self.is_opening = "No"
			return

		if not frappe.db.get_value(
			"Company", self.company, "book_advance_payments_in_separate_party_account"
		):
			self.is_opening = "No"
			return

		# Important to set this flag for the gl building logic to work properly
		self.book_advance_payments_in_separate_party_account = True
		account_type = frappe.get_value(
			"Account", {"name": self.party_account, "company": self.company}, "account_type"
		)

		if (account_type == "Payable" and self.party_type == "Customer") or (
			account_type == "Receivable" and self.party_type == "Supplier"
		):
			self.is_opening = "No"
			return

		if self.references:
			allowed_types = frozenset(["Sales Order", "Purchase Order"])
			reference_types = set([x.reference_doctype for x in self.references])

			# If there are referencers other than `allowed_types`, treat this as a normal payment entry
			if reference_types - allowed_types:
				self.book_advance_payments_in_separate_party_account = False
				self.is_opening = "No"
				return

		liability_account = get_party_account(
			self.party_type, self.party, self.company, include_advance=True
		)[1]

		self.set(self.party_account_field, liability_account)

		frappe.msgprint(
			_(
				"Book Advance Payments as Liability option is chosen. Paid From account changed from {0} to {1}."
			).format(
				frappe.bold(self.party_account),
				frappe.bold(liability_account),
			),
			alert=True,
		)

	def on_cancel(self):
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Payment Ledger Entry",
			"Repost Payment Ledger",
			"Repost Payment Ledger Items",
			"Repost Accounting Ledger",
			"Repost Accounting Ledger Items",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
		)
		super().on_cancel()
		self.make_gl_entries(cancel=1)
		self.update_outstanding_amounts()
		self.update_advance_paid()
		self.delink_advance_entry_references()
		self.update_payment_schedule(cancel=1)
		self.set_payment_req_status()
		self.set_status()

	def set_payment_req_status(self):
		from erpnext.accounts.doctype.payment_request.payment_request import update_payment_req_status

		update_payment_req_status(self, None)

	def update_outstanding_amounts(self):
		self.set_missing_ref_details(force=True)

	def validate_duplicate_entry(self):
		reference_names = []
		for d in self.get("references"):
			if (d.reference_doctype, d.reference_name, d.payment_term) in reference_names:
				frappe.throw(
					_("Row #{0}: Duplicate entry in References {1} {2}").format(
						d.idx, d.reference_doctype, d.reference_name
					)
				)
			reference_names.append((d.reference_doctype, d.reference_name, d.payment_term))

	def set_bank_account_data(self):
		if self.bank_account:
			bank_data = get_bank_account_details(self.bank_account)

			field = "paid_from" if self.payment_type == "Pay" else "paid_to"

			self.bank = bank_data.bank
			self.bank_account_no = bank_data.bank_account_no

			if not self.get(field):
				self.set(field, bank_data.account)

	def validate_payment_type_with_outstanding(self):
		total_outstanding = sum(d.allocated_amount for d in self.get("references"))
		if total_outstanding < 0 and self.party_type == "Customer" and self.payment_type == "Receive":
			frappe.throw(
				_("Cannot receive from customer against negative outstanding"),
				title=_("Incorrect Payment Type"),
			)

	def validate_allocated_amount(self):
		if self.payment_type == "Internal Transfer":
			return

		if self.party_type in ("Customer", "Supplier"):
			self.validate_allocated_amount_with_latest_data()
		else:
			fail_message = _("Row #{0}: Allocated Amount cannot be greater than outstanding amount.")
			for d in self.get("references"):
				if (flt(d.allocated_amount)) > 0 and flt(d.allocated_amount) > flt(d.outstanding_amount):
					frappe.throw(fail_message.format(d.idx))

				# Check for negative outstanding invoices as well
				if flt(d.allocated_amount) < 0 and flt(d.allocated_amount) < flt(d.outstanding_amount):
					frappe.throw(fail_message.format(d.idx))

	def term_based_allocation_enabled_for_reference(
		self, reference_doctype: str, reference_name: str
	) -> bool:
		if (
			reference_doctype
			and reference_doctype in ["Sales Invoice", "Sales Order", "Purchase Order", "Purchase Invoice"]
			and reference_name
		):
			if template := frappe.db.get_value(reference_doctype, reference_name, "payment_terms_template"):
				return frappe.db.get_value(
					"Payment Terms Template", template, "allocate_payment_based_on_payment_terms"
				)
		return False

	def validate_allocated_amount_with_latest_data(self):
		if self.references:
			uniq_vouchers = set([(x.reference_doctype, x.reference_name) for x in self.references])
			vouchers = [frappe._dict({"voucher_type": x[0], "voucher_no": x[1]}) for x in uniq_vouchers]
			latest_references = get_outstanding_reference_documents(
				{
					"posting_date": self.posting_date,
					"company": self.company,
					"party_type": self.party_type,
					"payment_type": self.payment_type,
					"party": self.party,
					"party_account": self.paid_from if self.payment_type == "Receive" else self.paid_to,
					"get_outstanding_invoices": True,
					"get_orders_to_be_billed": True,
					"vouchers": vouchers,
					"book_advance_payments_in_separate_party_account": self.book_advance_payments_in_separate_party_account,
				},
				validate=True,
			)

			# Group latest_references by (voucher_type, voucher_no)
			latest_lookup = {}
			for d in latest_references:
				d = frappe._dict(d)
				latest_lookup.setdefault((d.voucher_type, d.voucher_no), frappe._dict())[d.payment_term] = d

			for idx, d in enumerate(self.get("references"), start=1):
				latest = latest_lookup.get((d.reference_doctype, d.reference_name)) or frappe._dict()

				# If term based allocation is enabled, throw
				if (
					d.payment_term is None or d.payment_term == ""
				) and self.term_based_allocation_enabled_for_reference(d.reference_doctype, d.reference_name):
					frappe.throw(
						_(
							"{0} has Payment Term based allocation enabled. Select a Payment Term for Row #{1} in Payment References section"
						).format(frappe.bold(d.reference_name), frappe.bold(idx))
					)

				# if no payment template is used by invoice and has a custom term(no `payment_term`), then invoice outstanding will be in 'None' key
				latest = latest.get(d.payment_term) or latest.get(None)
				# The reference has already been fully paid
				if not latest:
					frappe.throw(
						_("{0} {1} has already been fully paid.").format(
							_(d.reference_doctype), d.reference_name
						)
					)
				# The reference has already been partly paid
				elif (
					latest.outstanding_amount < latest.invoice_amount
					and flt(d.outstanding_amount, d.precision("outstanding_amount"))
					!= flt(latest.outstanding_amount, d.precision("outstanding_amount"))
					and d.payment_term == ""
				):
					frappe.throw(
						_(
							"{0} {1} has already been partly paid. Please use the 'Get Outstanding Invoice' or the 'Get Outstanding Orders' button to get the latest outstanding amounts."
						).format(_(d.reference_doctype), d.reference_name)
					)

				fail_message = _("Row #{0}: Allocated Amount cannot be greater than outstanding amount.")

				if (
					d.payment_term
					and (
						(flt(d.allocated_amount)) > 0
						and latest.payment_term_outstanding
						and (flt(d.allocated_amount) > flt(latest.payment_term_outstanding))
					)
					and self.term_based_allocation_enabled_for_reference(
						d.reference_doctype, d.reference_name
					)
				):
					frappe.throw(
						_(
							"Row #{0}: Allocated amount:{1} is greater than outstanding amount:{2} for Payment Term {3}"
						).format(d.idx, d.allocated_amount, latest.payment_term_outstanding, d.payment_term)
					)

				if (flt(d.allocated_amount)) > 0 and flt(d.allocated_amount) > flt(latest.outstanding_amount):
					frappe.throw(fail_message.format(d.idx))

				# Check for negative outstanding invoices as well
				if flt(d.allocated_amount) < 0 and flt(d.allocated_amount) < flt(latest.outstanding_amount):
					frappe.throw(fail_message.format(d.idx))

	def delink_advance_entry_references(self):
		for reference in self.references:
			if reference.reference_doctype in ("Sales Invoice", "Purchase Invoice"):
				doc = frappe.get_doc(reference.reference_doctype, reference.reference_name)
				doc.delink_advance_entries(self.name)

	def set_missing_values(self):
		if self.payment_type == "Internal Transfer":
			for field in (
				"party",
				"party_balance",
				"total_allocated_amount",
				"base_total_allocated_amount",
				"unallocated_amount",
			):
				self.set(field, None)
			self.references = []
		else:
			if not self.party_type:
				frappe.throw(_("Party Type is mandatory"))

			if not self.party:
				frappe.throw(_("Party is mandatory"))

			_party_name = "title" if self.party_type == "Shareholder" else self.party_type.lower() + "_name"

			if frappe.db.has_column(self.party_type, _party_name):
				self.party_name = frappe.db.get_value(self.party_type, self.party, _party_name)
			else:
				self.party_name = frappe.db.get_value(self.party_type, self.party, "name")

		if self.party:
			if not self.party_balance:
				self.party_balance = get_balance_on(
					party_type=self.party_type, party=self.party, date=self.posting_date, company=self.company
				)

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

		self.party_account_currency = (
			self.paid_from_account_currency
			if self.payment_type == "Receive"
			else self.paid_to_account_currency
		)

	def set_missing_ref_details(
		self,
		force: bool = False,
		update_ref_details_only_for: list | None = None,
		reference_exchange_details: dict | None = None,
	) -> None:
		for d in self.get("references"):
			if d.allocated_amount:
				if update_ref_details_only_for and (
					(d.reference_doctype, d.reference_name) not in update_ref_details_only_for
				):
					continue

				ref_details = get_reference_details(
					d.reference_doctype,
					d.reference_name,
					self.party_account_currency,
					self.party_type,
					self.party,
				)

				# Only update exchange rate when the reference is Journal Entry
				if (
					reference_exchange_details
					and d.reference_doctype == reference_exchange_details.reference_doctype
					and d.reference_name == reference_exchange_details.reference_name
				):
					ref_details.update({"exchange_rate": reference_exchange_details.exchange_rate})

				for field, value in ref_details.items():
					if d.exchange_gain_loss:
						# for cases where gain/loss is booked into invoice
						# exchange_gain_loss is calculated from invoice & populated
						# and row.exchange_rate is already set to payment entry's exchange rate
						# refer -> `update_reference_in_payment_entry()` in utils.py
						continue

					if field == "exchange_rate" or not d.get(field) or force:
						d.db_set(field, value)

	def validate_payment_type(self):
		if self.payment_type not in ("Receive", "Pay", "Internal Transfer"):
			frappe.throw(_("Payment Type must be one of Receive, Pay and Internal Transfer"))

	def validate_party_details(self):
		if self.party:
			if not frappe.db.exists(self.party_type, self.party):
				frappe.throw(_("{0} {1} does not exist").format(_(self.party_type), self.party))

	def set_exchange_rate(self, ref_doc=None):
		self.set_source_exchange_rate(ref_doc)
		self.set_target_exchange_rate(ref_doc)

	def set_source_exchange_rate(self, ref_doc=None):
		if self.paid_from:
			if self.paid_from_account_currency == self.company_currency:
				self.source_exchange_rate = 1
			else:
				if ref_doc:
					if self.paid_from_account_currency == ref_doc.currency:
						self.source_exchange_rate = ref_doc.get("exchange_rate") or ref_doc.get(
							"conversion_rate"
						)

			if not self.source_exchange_rate:
				self.source_exchange_rate = get_exchange_rate(
					self.paid_from_account_currency, self.company_currency, self.posting_date
				)

	def set_target_exchange_rate(self, ref_doc=None):
		if self.paid_from_account_currency == self.paid_to_account_currency:
			self.target_exchange_rate = self.source_exchange_rate
		elif self.paid_to and not self.target_exchange_rate:
			if ref_doc:
				if self.paid_to_account_currency == ref_doc.currency:
					self.target_exchange_rate = ref_doc.get("exchange_rate") or ref_doc.get("conversion_rate")

			if not self.target_exchange_rate:
				self.target_exchange_rate = get_exchange_rate(
					self.paid_to_account_currency, self.company_currency, self.posting_date
				)

	def validate_mandatory(self):
		for field in ("paid_amount", "received_amount", "source_exchange_rate", "target_exchange_rate"):
			if not self.get(field):
				frappe.throw(_("{0} is mandatory").format(self.meta.get_label(field)))

	def validate_reference_documents(self):
		valid_reference_doctypes = self.get_valid_reference_doctypes()

		if not valid_reference_doctypes:
			return

		for d in self.get("references"):
			if not d.allocated_amount:
				continue
			if d.reference_doctype not in valid_reference_doctypes:
				frappe.throw(
					_("Reference Doctype must be one of {0}").format(
						comma_or(_(d) for d in valid_reference_doctypes)
					)
				)

			elif d.reference_name:
				if not frappe.db.exists(d.reference_doctype, d.reference_name):
					frappe.throw(_("{0} {1} does not exist").format(d.reference_doctype, d.reference_name))
				else:
					ref_doc = frappe.get_doc(d.reference_doctype, d.reference_name)

					if d.reference_doctype != "Journal Entry":
						if self.party != ref_doc.get(scrub(self.party_type)):
							frappe.throw(
								_("{0} {1} is not associated with {2} {3}").format(
									_(d.reference_doctype), d.reference_name, _(self.party_type), self.party
								)
							)
					else:
						self.validate_journal_entry()

					if d.reference_doctype in frappe.get_hooks("invoice_doctypes"):
						if self.party_type == "Customer":
							ref_party_account = (
								get_party_account_based_on_invoice_discounting(d.reference_name)
								or ref_doc.debit_to
							)
						elif self.party_type == "Supplier":
							ref_party_account = ref_doc.credit_to
						elif self.party_type == "Employee":
							ref_party_account = ref_doc.payable_account

						if (
							ref_party_account != self.party_account
							and not self.book_advance_payments_in_separate_party_account
						):
							frappe.throw(
								_("{0} {1} is associated with {2}, but Party Account is {3}").format(
									_(d.reference_doctype),
									d.reference_name,
									ref_party_account,
									self.party_account,
								)
							)

						if ref_doc.doctype == "Purchase Invoice" and ref_doc.get("on_hold"):
							frappe.throw(
								_("{0} {1} is on hold").format(_(d.reference_doctype), d.reference_name),
								title=_("Invalid Purchase Invoice"),
							)

					if ref_doc.docstatus != 1:
						frappe.throw(
							_("{0} {1} must be submitted").format(_(d.reference_doctype), d.reference_name)
						)

	def get_valid_reference_doctypes(self):
		if self.party_type == "Customer":
			return ("Sales Order", "Sales Invoice", "Journal Entry", "Dunning", "Payment Entry")
		elif self.party_type == "Supplier":
			return ("Purchase Order", "Purchase Invoice", "Journal Entry", "Payment Entry")
		elif self.party_type == "Shareholder":
			return ("Journal Entry",)
		elif self.party_type == "Employee":
			return ("Journal Entry",)

	def validate_paid_invoices(self):
		no_oustanding_refs = {}

		for d in self.get("references"):
			if not d.allocated_amount:
				continue

			if d.reference_doctype in ("Sales Invoice", "Purchase Invoice"):
				outstanding_amount, is_return = frappe.get_cached_value(
					d.reference_doctype, d.reference_name, ["outstanding_amount", "is_return"]
				)
				if outstanding_amount <= 0 and not is_return:
					no_oustanding_refs.setdefault(d.reference_doctype, []).append(d)

		for reference_doctype, references in no_oustanding_refs.items():
			frappe.msgprint(
				_(
					"References {0} of type {1} had no outstanding amount left before submitting the Payment Entry. Now they have a negative outstanding amount."
				).format(
					frappe.bold(comma_and([d.reference_name for d in references])),
					_(reference_doctype),
				)
				+ "<br><br>"
				+ _("If this is undesirable please cancel the corresponding Payment Entry."),
				title=_("Warning"),
				indicator="orange",
			)

	def validate_journal_entry(self):
		for d in self.get("references"):
			if d.allocated_amount and d.reference_doctype == "Journal Entry":
				je_accounts = frappe.db.sql(
					"""select debit, credit from `tabJournal Entry Account`
					where account = %s and party=%s and docstatus = 1 and parent = %s
					and (reference_type is null or reference_type in ("", "Sales Order", "Purchase Order"))
					""",
					(self.party_account, self.party, d.reference_name),
					as_dict=True,
				)

				if not je_accounts:
					frappe.throw(
						_(
							"Row #{0}: Journal Entry {1} does not have account {2} or already matched against another voucher"
						).format(d.idx, d.reference_name, self.party_account)
					)
				else:
					dr_or_cr = "debit" if self.payment_type == "Receive" else "credit"
					valid = False
					for jvd in je_accounts:
						if flt(jvd[dr_or_cr]) > 0:
							valid = True
					if not valid:
						frappe.throw(
							_("Against Journal Entry {0} does not have any unmatched {1} entry").format(
								d.reference_name, _(dr_or_cr)
							)
						)

	def update_payment_schedule(self, cancel=0):
		invoice_payment_amount_map = {}
		invoice_paid_amount_map = {}

		for ref in self.get("references"):
			if ref.payment_term and ref.reference_name:
				key = (ref.payment_term, ref.reference_name, ref.reference_doctype)
				invoice_payment_amount_map.setdefault(key, 0.0)
				invoice_payment_amount_map[key] += ref.allocated_amount

				if not invoice_paid_amount_map.get(key):
					payment_schedule = frappe.get_all(
						"Payment Schedule",
						filters={"parent": ref.reference_name},
						fields=[
							"paid_amount",
							"payment_amount",
							"payment_term",
							"discount",
							"outstanding",
							"discount_type",
						],
					)
					for term in payment_schedule:
						invoice_key = (term.payment_term, ref.reference_name, ref.reference_doctype)
						invoice_paid_amount_map.setdefault(invoice_key, {})
						invoice_paid_amount_map[invoice_key]["outstanding"] = term.outstanding
						if not (term.discount_type and term.discount):
							continue

						if term.discount_type == "Percentage":
							invoice_paid_amount_map[invoice_key]["discounted_amt"] = ref.total_amount * (
								term.discount / 100
							)
						else:
							invoice_paid_amount_map[invoice_key]["discounted_amt"] = term.discount

		for idx, (key, allocated_amount) in enumerate(invoice_payment_amount_map.items(), 1):
			if not invoice_paid_amount_map.get(key):
				frappe.throw(_("Payment term {0} not used in {1}").format(key[0], key[1]))

			allocated_amount = self.get_allocated_amount_in_transaction_currency(
				allocated_amount, key[2], key[1]
			)

			outstanding = flt(invoice_paid_amount_map.get(key, {}).get("outstanding"))
			discounted_amt = flt(invoice_paid_amount_map.get(key, {}).get("discounted_amt"))

			if cancel:
				frappe.db.sql(
					"""
					UPDATE `tabPayment Schedule`
					SET
						paid_amount = `paid_amount` - %s,
						discounted_amount = `discounted_amount` - %s,
						outstanding = `outstanding` + %s
					WHERE parent = %s and payment_term = %s""",
					(allocated_amount - discounted_amt, discounted_amt, allocated_amount, key[1], key[0]),
				)
			else:
				if allocated_amount > outstanding:
					frappe.throw(
						_("Row #{0}: Cannot allocate more than {1} against payment term {2}").format(
							idx, fmt_money(outstanding), key[0]
						)
					)

				if allocated_amount and outstanding:
					frappe.db.sql(
						"""
						UPDATE `tabPayment Schedule`
						SET
							paid_amount = `paid_amount` + %s,
							discounted_amount = `discounted_amount` + %s,
							outstanding = `outstanding` - %s
						WHERE parent = %s and payment_term = %s""",
						(allocated_amount - discounted_amt, discounted_amt, allocated_amount, key[1], key[0]),
					)

	def get_allocated_amount_in_transaction_currency(
		self, allocated_amount, reference_doctype, reference_docname
	):
		"""
		Payment Entry could be in base currency while reference's payment schedule
		is always in transaction currency.
		E.g.
		* SI with base=INR and currency=USD
		* SI with payment schedule in USD
		* PE in INR (accounting done in base currency)
		"""
		ref_currency, ref_exchange_rate = frappe.db.get_value(
			reference_doctype, reference_docname, ["currency", "conversion_rate"]
		)
		is_single_currency = self.paid_from_account_currency == self.paid_to_account_currency
		# PE in different currency
		reference_is_multi_currency = self.paid_from_account_currency != ref_currency

		if not (is_single_currency and reference_is_multi_currency):
			return allocated_amount

		allocated_amount = flt(allocated_amount / ref_exchange_rate, self.precision("total_allocated_amount"))

		return allocated_amount

	def set_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
		elif self.docstatus == 1:
			self.status = "Submitted"
		else:
			self.status = "Draft"

		self.db_set("status", self.status, update_modified=True)

	def set_total_in_words(self):
		from frappe.utils import money_in_words

		if self.payment_type in ("Pay", "Internal Transfer"):
			base_amount = abs(self.base_paid_amount)
			amount = abs(self.paid_amount)
			currency = self.paid_from_account_currency
		elif self.payment_type == "Receive":
			base_amount = abs(self.base_received_amount)
			amount = abs(self.received_amount)
			currency = self.paid_to_account_currency

		self.base_in_words = money_in_words(base_amount, self.company_currency)
		self.in_words = money_in_words(amount, currency)

	def set_tax_withholding(self):
		if not self.party_type == "Supplier":
			return

		if not self.apply_tax_withholding_amount:
			return

		net_total = self.calculate_tax_withholding_net_total()

		# Adding args as purchase invoice to get TDS amount
		args = frappe._dict(
			{
				"company": self.company,
				"doctype": "Payment Entry",
				"supplier": self.party,
				"posting_date": self.posting_date,
				"net_total": net_total,
			}
		)

		tax_withholding_details = get_party_tax_withholding_details(args, self.tax_withholding_category)

		if not tax_withholding_details:
			return

		tax_withholding_details.update(
			{"cost_center": self.cost_center or erpnext.get_default_cost_center(self.company)}
		)

		accounts = []
		for d in self.taxes:
			if d.account_head == tax_withholding_details.get("account_head"):
				# Preserve user updated included in paid amount
				if d.included_in_paid_amount:
					tax_withholding_details.update({"included_in_paid_amount": d.included_in_paid_amount})

				d.update(tax_withholding_details)
			accounts.append(d.account_head)

		if not accounts or tax_withholding_details.get("account_head") not in accounts:
			self.append("taxes", tax_withholding_details)

		to_remove = [
			d
			for d in self.taxes
			if not d.tax_amount and d.account_head == tax_withholding_details.get("account_head")
		]

		for d in to_remove:
			self.remove(d)

	def calculate_tax_withholding_net_total(self):
		net_total = 0
		order_details = self.get_order_wise_tax_withholding_net_total()

		for d in self.references:
			tax_withholding_net_total = order_details.get(d.reference_name)
			if not tax_withholding_net_total:
				continue

			net_taxable_outstanding = max(
				0, d.outstanding_amount - (d.total_amount - tax_withholding_net_total)
			)

			net_total += min(net_taxable_outstanding, d.allocated_amount)

		net_total += self.unallocated_amount

		return net_total

	def get_order_wise_tax_withholding_net_total(self):
		if self.party_type == "Supplier":
			doctype = "Purchase Order"
		else:
			doctype = "Sales Order"

		docnames = [d.reference_name for d in self.references if d.reference_doctype == doctype]

		return frappe._dict(
			frappe.db.get_all(
				doctype,
				filters={"name": ["in", docnames]},
				fields=["name", "base_tax_withholding_net_total"],
				as_list=True,
			)
		)

	def apply_taxes(self):
		self.initialize_taxes()
		self.determine_exclusive_rate()
		self.calculate_taxes()

	def set_amounts(self):
		self.set_received_amount()
		self.set_amounts_in_company_currency()
		self.set_total_allocated_amount()
		self.set_unallocated_amount()
		self.set_difference_amount()

	def validate_amounts(self):
		self.validate_received_amount()

	def validate_received_amount(self):
		if self.paid_from_account_currency == self.paid_to_account_currency:
			if self.paid_amount < self.received_amount:
				frappe.throw(_("Received Amount cannot be greater than Paid Amount"))

	def set_received_amount(self):
		self.base_received_amount = self.base_paid_amount
		if (
			self.paid_from_account_currency == self.paid_to_account_currency
			and not self.payment_type == "Internal Transfer"
		):
			self.received_amount = self.paid_amount

	def set_amounts_after_tax(self):
		applicable_tax = 0
		base_applicable_tax = 0
		for tax in self.get("taxes"):
			if not tax.included_in_paid_amount:
				amount = -1 * tax.tax_amount if tax.add_deduct_tax == "Deduct" else tax.tax_amount
				base_amount = (
					-1 * tax.base_tax_amount if tax.add_deduct_tax == "Deduct" else tax.base_tax_amount
				)

				applicable_tax += amount
				base_applicable_tax += base_amount

		self.paid_amount_after_tax = flt(
			flt(self.paid_amount) + flt(applicable_tax), self.precision("paid_amount_after_tax")
		)
		self.base_paid_amount_after_tax = flt(
			flt(self.paid_amount_after_tax) * flt(self.source_exchange_rate),
			self.precision("base_paid_amount_after_tax"),
		)

		self.received_amount_after_tax = flt(
			flt(self.received_amount) + flt(applicable_tax), self.precision("paid_amount_after_tax")
		)
		self.base_received_amount_after_tax = flt(
			flt(self.received_amount_after_tax) * flt(self.target_exchange_rate),
			self.precision("base_paid_amount_after_tax"),
		)

	def set_amounts_in_company_currency(self):
		self.base_paid_amount, self.base_received_amount, self.difference_amount = 0, 0, 0
		if self.paid_amount:
			self.base_paid_amount = flt(
				flt(self.paid_amount) * flt(self.source_exchange_rate), self.precision("base_paid_amount")
			)

		if self.received_amount:
			self.base_received_amount = flt(
				flt(self.received_amount) * flt(self.target_exchange_rate),
				self.precision("base_received_amount"),
			)

	def calculate_base_allocated_amount_for_reference(self, d) -> float:
		base_allocated_amount = 0
		if d.reference_doctype in frappe.get_hooks("advance_payment_doctypes"):
			# When referencing Sales/Purchase Order, use the source/target exchange rate depending on payment type.
			# This is so there are no Exchange Gain/Loss generated for such doctypes

			exchange_rate = 1
			if self.payment_type == "Receive":
				exchange_rate = self.source_exchange_rate
			elif self.payment_type == "Pay":
				exchange_rate = self.target_exchange_rate

			base_allocated_amount += flt(
				flt(d.allocated_amount) * flt(exchange_rate), self.precision("base_paid_amount")
			)
		else:
			# Use source/target exchange rate, so no difference amount is calculated.
			# then update exchange gain/loss amount in reference table
			# if there is an exchange gain/loss amount in reference table, submit a JE for that

			exchange_rate = 1
			if self.payment_type == "Receive":
				exchange_rate = self.source_exchange_rate
			elif self.payment_type == "Pay":
				exchange_rate = self.target_exchange_rate

			base_allocated_amount += flt(
				flt(d.allocated_amount) * flt(exchange_rate), self.precision("base_paid_amount")
			)

			# on rare case, when `exchange_rate` is unset, gain/loss amount is incorrectly calculated
			# for base currency transactions
			if d.exchange_rate is None:
				d.exchange_rate = 1

			allocated_amount_in_pe_exchange_rate = flt(
				flt(d.allocated_amount) * flt(d.exchange_rate), self.precision("base_paid_amount")
			)
			d.exchange_gain_loss = base_allocated_amount - allocated_amount_in_pe_exchange_rate
		return base_allocated_amount

	def set_total_allocated_amount(self):
		if self.payment_type == "Internal Transfer":
			return

		total_allocated_amount, base_total_allocated_amount = 0, 0
		for d in self.get("references"):
			if d.allocated_amount:
				total_allocated_amount += flt(d.allocated_amount)
				base_total_allocated_amount += self.calculate_base_allocated_amount_for_reference(d)

		self.total_allocated_amount = abs(total_allocated_amount)
		self.base_total_allocated_amount = abs(base_total_allocated_amount)

	def set_unallocated_amount(self):
		self.unallocated_amount = 0
		if self.party:
			total_deductions = sum(flt(d.amount) for d in self.get("deductions"))
			included_taxes = self.get_included_taxes()
			if (
				self.payment_type == "Receive"
				and self.base_total_allocated_amount < self.base_received_amount + total_deductions
				and self.total_allocated_amount
				< flt(self.paid_amount) + (total_deductions / self.source_exchange_rate)
			):
				self.unallocated_amount = (
					self.base_received_amount + total_deductions - self.base_total_allocated_amount
				) / self.source_exchange_rate
				self.unallocated_amount -= included_taxes
			elif (
				self.payment_type == "Pay"
				and self.base_total_allocated_amount < (self.base_paid_amount - total_deductions)
				and self.total_allocated_amount
				< flt(self.received_amount) + (total_deductions / self.target_exchange_rate)
			):
				self.unallocated_amount = (
					self.base_paid_amount - (total_deductions + self.base_total_allocated_amount)
				) / self.target_exchange_rate
				self.unallocated_amount -= included_taxes

	def set_difference_amount(self):
		base_unallocated_amount = flt(self.unallocated_amount) * (
			flt(self.source_exchange_rate)
			if self.payment_type == "Receive"
			else flt(self.target_exchange_rate)
		)

		base_party_amount = flt(self.base_total_allocated_amount) + flt(base_unallocated_amount)
		included_taxes = self.get_included_taxes()

		if self.payment_type == "Receive":
			self.difference_amount = base_party_amount - self.base_received_amount + included_taxes
		elif self.payment_type == "Pay":
			self.difference_amount = self.base_paid_amount - base_party_amount - included_taxes
		else:
			self.difference_amount = self.base_paid_amount - flt(self.base_received_amount) - included_taxes

		total_deductions = sum(flt(d.amount) for d in self.get("deductions"))

		self.difference_amount = flt(
			self.difference_amount - total_deductions, self.precision("difference_amount")
		)

	def get_included_taxes(self):
		included_taxes = 0
		for tax in self.get("taxes"):
			if tax.included_in_paid_amount:
				if tax.add_deduct_tax == "Add":
					included_taxes += tax.base_tax_amount
				else:
					included_taxes -= tax.base_tax_amount

		return included_taxes

	# Paid amount is auto allocated in the reference document by default.
	# Clear the reference document which doesn't have allocated amount on validate so that form can be loaded fast
	def clear_unallocated_reference_document_rows(self):
		self.set("references", self.get("references", {"allocated_amount": ["not in", [0, None, ""]]}))
		frappe.db.sql(
			"""delete from `tabPayment Entry Reference`
			where parent = %s and allocated_amount = 0""",
			self.name,
		)

	def set_title(self):
		if frappe.flags.in_import and self.title:
			# do not set title dynamically if title exists during data import.
			return

		if self.payment_type in ("Receive", "Pay"):
			self.title = self.party
		else:
			self.title = self.paid_from + " - " + self.paid_to

	def validate_transaction_reference(self):
		bank_account = self.paid_to if self.payment_type == "Receive" else self.paid_from
		bank_account_type = frappe.get_cached_value("Account", bank_account, "account_type")

		if bank_account_type == "Bank":
			if not self.reference_no or not self.reference_date:
				frappe.throw(_("Reference No and Reference Date is mandatory for Bank transaction"))

	def set_remarks(self):
		if self.custom_remarks:
			return

		if self.payment_type == "Internal Transfer":
			remarks = [
				_("Amount {0} {1} transferred from {2} to {3}").format(
					_(self.paid_from_account_currency), self.paid_amount, self.paid_from, self.paid_to
				)
			]
		else:
			remarks = [
				_("Amount {0} {1} {2} {3}").format(
					_(self.party_account_currency),
					self.paid_amount if self.payment_type == "Receive" else self.received_amount,
					_("received from") if self.payment_type == "Receive" else _("to"),
					self.party,
				)
			]

		if self.reference_no:
			remarks.append(
				_("Transaction reference no {0} dated {1}").format(self.reference_no, self.reference_date)
			)

		if self.payment_type in ["Receive", "Pay"]:
			for d in self.get("references"):
				if d.allocated_amount:
					remarks.append(
						_("Amount {0} {1} against {2} {3}").format(
							_(self.party_account_currency),
							d.allocated_amount,
							d.reference_doctype,
							d.reference_name,
						)
					)

		for d in self.get("deductions"):
			if d.amount:
				remarks.append(
					_("Amount {0} {1} deducted against {2}").format(
						_(self.company_currency), d.amount, d.account
					)
				)

		self.set("remarks", "\n".join(remarks))

	def build_gl_map(self):
		if self.payment_type in ("Receive", "Pay") and not self.get("party_account_field"):
			self.setup_party_account_field()

		gl_entries = []
		self.add_party_gl_entries(gl_entries)
		self.add_bank_gl_entries(gl_entries)
		self.add_deductions_gl_entries(gl_entries)
		self.add_tax_gl_entries(gl_entries)
		add_regional_gl_entries(gl_entries, self)
		return gl_entries

	def make_gl_entries(self, cancel=0, adv_adj=0):
		gl_entries = self.build_gl_map()
		gl_entries = process_gl_map(gl_entries)
		make_gl_entries(gl_entries, cancel=cancel, adv_adj=adv_adj)
		if cancel:
			cancel_exchange_gain_loss_journal(frappe._dict(doctype=self.doctype, name=self.name))
		else:
			self.make_exchange_gain_loss_journal()

		self.make_advance_gl_entries(cancel=cancel)

	def add_party_gl_entries(self, gl_entries):
		if self.party_account:
			if self.payment_type == "Receive":
				against_account = self.paid_to
			else:
				against_account = self.paid_from

			party_gl_dict = self.get_gl_dict(
				{
					"account": self.party_account,
					"party_type": self.party_type,
					"party": self.party,
					"against": against_account,
					"account_currency": self.party_account_currency,
					"cost_center": self.cost_center,
				},
				item=self,
			)

			dr_or_cr = "credit" if self.payment_type == "Receive" else "debit"

			for d in self.get("references"):
				# re-defining dr_or_cr for every reference in order to avoid the last value affecting calculation of reverse
				dr_or_cr = "credit" if self.payment_type == "Receive" else "debit"
				cost_center = self.cost_center
				if d.reference_doctype == "Sales Invoice" and not cost_center:
					cost_center = frappe.db.get_value(d.reference_doctype, d.reference_name, "cost_center")

				gle = party_gl_dict.copy()

				allocated_amount_in_company_currency = self.calculate_base_allocated_amount_for_reference(d)
				reverse_dr_or_cr = 0

				if d.reference_doctype in ["Sales Invoice", "Purchase Invoice"]:
					is_return = frappe.db.get_value(d.reference_doctype, d.reference_name, "is_return")
					payable_party_types = get_party_types_from_account_type("Payable")
					receivable_party_types = get_party_types_from_account_type("Receivable")
					if (
						is_return
						and self.party_type in receivable_party_types
						and (self.payment_type == "Pay")
					):
						reverse_dr_or_cr = 1
					elif (
						is_return
						and self.party_type in payable_party_types
						and (self.payment_type == "Receive")
					):
						reverse_dr_or_cr = 1

					if is_return and not reverse_dr_or_cr:
						dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

				gle.update(
					{
						dr_or_cr: abs(allocated_amount_in_company_currency),
						dr_or_cr + "_in_account_currency": abs(d.allocated_amount),
						"against_voucher_type": d.reference_doctype,
						"against_voucher": d.reference_name,
						"cost_center": cost_center,
					}
				)
				gl_entries.append(gle)

			if self.unallocated_amount:
				dr_or_cr = "credit" if self.payment_type == "Receive" else "debit"
				exchange_rate = self.get_exchange_rate()
				base_unallocated_amount = self.unallocated_amount * exchange_rate

				gle = party_gl_dict.copy()
				gle.update(
					{
						dr_or_cr + "_in_account_currency": self.unallocated_amount,
						dr_or_cr: base_unallocated_amount,
					}
				)

				if self.book_advance_payments_in_separate_party_account:
					gle.update(
						{
							"against_voucher_type": "Payment Entry",
							"against_voucher": self.name,
						}
					)
				gl_entries.append(gle)

	def make_advance_gl_entries(
		self, entry: object | dict = None, cancel: bool = 0, update_outstanding: str = "Yes"
	):
		gl_entries = []
		self.add_advance_gl_entries(gl_entries, entry)

		if cancel:
			make_reverse_gl_entries(gl_entries, partial_cancel=True)
		else:
			make_gl_entries(gl_entries, update_outstanding=update_outstanding)

	def add_advance_gl_entries(self, gl_entries: list, entry: object | dict | None):
		"""
		If 'entry' is passed, GL entries only for that reference is added.
		"""
		if self.book_advance_payments_in_separate_party_account:
			references = [x for x in self.get("references")]
			if entry:
				references = [x for x in self.get("references") if x.name == entry.name]

			for ref in references:
				if ref.reference_doctype in (
					"Sales Invoice",
					"Purchase Invoice",
					"Journal Entry",
					"Payment Entry",
				):
					self.add_advance_gl_for_reference(gl_entries, ref)

	def get_dr_and_account_for_advances(self, reference):
		if reference.reference_doctype == "Sales Invoice":
			return "credit", reference.account

		if reference.reference_doctype == "Purchase Invoice":
			return "debit", reference.account

		if reference.reference_doctype == "Payment Entry":
			# reference.account_type and reference.payment_type is only available for Reverse payments
			if reference.account_type == "Receivable" and reference.payment_type == "Pay":
				return "credit", self.party_account
			else:
				return "debit", self.party_account

		if reference.reference_doctype == "Journal Entry":
			if self.party_type == "Customer" and self.payment_type == "Receive":
				return "credit", reference.account
			else:
				return "debit", reference.account

	def add_advance_gl_for_reference(self, gl_entries, invoice):
		args_dict = {
			"party_type": self.party_type,
			"party": self.party,
			"account_currency": self.party_account_currency,
			"cost_center": self.cost_center,
			"voucher_type": "Payment Entry",
			"voucher_no": self.name,
			"voucher_detail_no": invoice.name,
		}

		if self.reconcile_on_advance_payment_date:
			posting_date = self.posting_date
		else:
			date_field = "posting_date"
			if invoice.reference_doctype in ["Sales Order", "Purchase Order"]:
				date_field = "transaction_date"
			posting_date = frappe.db.get_value(invoice.reference_doctype, invoice.reference_name, date_field)

			if getdate(posting_date) < getdate(self.posting_date):
				posting_date = self.posting_date

		dr_or_cr, account = self.get_dr_and_account_for_advances(invoice)
		args_dict["account"] = account
		args_dict[dr_or_cr] = self.calculate_base_allocated_amount_for_reference(invoice)
		args_dict[dr_or_cr + "_in_account_currency"] = invoice.allocated_amount
		args_dict.update(
			{
				"against_voucher_type": invoice.reference_doctype,
				"against_voucher": invoice.reference_name,
				"posting_date": posting_date,
			}
		)
		gle = self.get_gl_dict(
			args_dict,
			item=self,
		)
		gl_entries.append(gle)

		args_dict[dr_or_cr] = 0
		args_dict[dr_or_cr + "_in_account_currency"] = 0
		dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"
		args_dict["account"] = self.party_account
		args_dict[dr_or_cr] = self.calculate_base_allocated_amount_for_reference(invoice)
		args_dict[dr_or_cr + "_in_account_currency"] = invoice.allocated_amount
		args_dict.update(
			{
				"against_voucher_type": "Payment Entry",
				"against_voucher": self.name,
			}
		)
		gle = self.get_gl_dict(
			args_dict,
			item=self,
		)
		gl_entries.append(gle)

	def add_bank_gl_entries(self, gl_entries):
		if self.payment_type in ("Pay", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.paid_from,
						"account_currency": self.paid_from_account_currency,
						"against": self.party if self.payment_type == "Pay" else self.paid_to,
						"credit_in_account_currency": self.paid_amount,
						"credit": self.base_paid_amount,
						"cost_center": self.cost_center,
						"post_net_value": True,
					},
					item=self,
				)
			)
		if self.payment_type in ("Receive", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": self.paid_to,
						"account_currency": self.paid_to_account_currency,
						"against": self.party if self.payment_type == "Receive" else self.paid_from,
						"debit_in_account_currency": self.received_amount,
						"debit": self.base_received_amount,
						"cost_center": self.cost_center,
					},
					item=self,
				)
			)

	def add_tax_gl_entries(self, gl_entries):
		for d in self.get("taxes"):
			account_currency = get_account_currency(d.account_head)
			if account_currency != self.company_currency:
				frappe.throw(_("Currency for {0} must be {1}").format(d.account_head, self.company_currency))

			if self.payment_type in ("Pay", "Internal Transfer"):
				dr_or_cr = "debit" if d.add_deduct_tax == "Add" else "credit"
				rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
				against = self.party or self.paid_from
			elif self.payment_type == "Receive":
				dr_or_cr = "credit" if d.add_deduct_tax == "Add" else "debit"
				rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
				against = self.party or self.paid_to

			payment_account = self.get_party_account_for_taxes()
			tax_amount = d.tax_amount
			base_tax_amount = d.base_tax_amount

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": d.account_head,
						"against": against,
						dr_or_cr: tax_amount,
						dr_or_cr + "_in_account_currency": base_tax_amount
						if account_currency == self.company_currency
						else d.tax_amount,
						"cost_center": d.cost_center,
						"post_net_value": True,
					},
					account_currency,
					item=d,
				)
			)

			if not d.included_in_paid_amount:
				if get_account_currency(payment_account) != self.company_currency:
					if self.payment_type == "Receive":
						exchange_rate = self.target_exchange_rate
					elif self.payment_type in ["Pay", "Internal Transfer"]:
						exchange_rate = self.source_exchange_rate
					base_tax_amount = flt((tax_amount / exchange_rate), self.precision("paid_amount"))

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": payment_account,
							"against": against,
							rev_dr_or_cr: tax_amount,
							rev_dr_or_cr + "_in_account_currency": base_tax_amount
							if account_currency == self.company_currency
							else d.tax_amount,
							"cost_center": self.cost_center,
							"post_net_value": True,
						},
						account_currency,
						item=d,
					)
				)

	def add_deductions_gl_entries(self, gl_entries):
		for d in self.get("deductions"):
			if d.amount:
				account_currency = get_account_currency(d.account)
				if account_currency != self.company_currency:
					frappe.throw(_("Currency for {0} must be {1}").format(d.account, self.company_currency))

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": d.account,
							"account_currency": account_currency,
							"against": self.party or self.paid_from,
							"debit_in_account_currency": d.amount,
							"debit": d.amount,
							"cost_center": d.cost_center,
						},
						item=d,
					)
				)

	def get_party_account_for_taxes(self):
		if self.payment_type == "Receive":
			return self.paid_to
		elif self.payment_type in ("Pay", "Internal Transfer"):
			return self.paid_from

	def update_advance_paid(self):
		if self.payment_type in ("Receive", "Pay") and self.party:
			for d in self.get("references"):
				if d.allocated_amount and d.reference_doctype in frappe.get_hooks("advance_payment_doctypes"):
					frappe.get_doc(
						d.reference_doctype, d.reference_name, for_update=True
					).set_total_advance_paid()

	def on_recurring(self, reference_doc, auto_repeat_doc):
		self.reference_no = reference_doc.name
		self.reference_date = nowdate()

	def calculate_deductions(self, tax_details):
		return {
			"account": tax_details["tax"]["account_head"],
			"cost_center": frappe.get_cached_value("Company", self.company, "cost_center"),
			"amount": self.total_allocated_amount * (tax_details["tax"]["rate"] / 100),
		}

	def set_gain_or_loss(self, account_details=None):
		if not self.difference_amount:
			self.set_difference_amount()

		row = {"amount": self.difference_amount}

		if account_details:
			row.update(account_details)

		if not row.get("amount"):
			# if no difference amount
			return

		self.append("deductions", row)
		self.set_unallocated_amount()

	def get_exchange_rate(self):
		return self.source_exchange_rate if self.payment_type == "Receive" else self.target_exchange_rate

	def initialize_taxes(self):
		for tax in self.get("taxes"):
			validate_taxes_and_charges(tax)
			validate_inclusive_tax(tax, self)

			tax_fields = ["total", "tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if tax.charge_type != "Actual":
				tax_fields.append("tax_amount")

			for fieldname in tax_fields:
				tax.set(fieldname, 0.0)

		self.paid_amount_after_tax = self.base_paid_amount

	def determine_exclusive_rate(self):
		if not any(cint(tax.included_in_paid_amount) for tax in self.get("taxes")):
			return

		cumulated_tax_fraction = 0
		for i, tax in enumerate(self.get("taxes")):
			tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax)
			if i == 0:
				tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
			else:
				tax.grand_total_fraction_for_current_item = (
					self.get("taxes")[i - 1].grand_total_fraction_for_current_item
					+ tax.tax_fraction_for_current_item
				)

			cumulated_tax_fraction += tax.tax_fraction_for_current_item

		self.paid_amount_after_tax = flt(self.base_paid_amount / (1 + cumulated_tax_fraction))

	def calculate_taxes(self):
		self.total_taxes_and_charges = 0.0
		self.base_total_taxes_and_charges = 0.0

		actual_tax_dict = dict(
			[
				[tax.idx, flt(tax.tax_amount, tax.precision("tax_amount"))]
				for tax in self.get("taxes")
				if tax.charge_type == "Actual"
			]
		)

		for i, tax in enumerate(self.get("taxes")):
			current_tax_amount = self.get_current_tax_amount(tax)

			if tax.charge_type == "Actual":
				actual_tax_dict[tax.idx] -= current_tax_amount
				if i == len(self.get("taxes")) - 1:
					current_tax_amount += actual_tax_dict[tax.idx]

			tax.tax_amount = current_tax_amount
			tax.base_tax_amount = current_tax_amount

			if tax.add_deduct_tax == "Deduct":
				current_tax_amount *= -1.0
			else:
				current_tax_amount *= 1.0

			if i == 0:
				tax.total = flt(self.paid_amount_after_tax + current_tax_amount, self.precision("total", tax))
			else:
				tax.total = flt(
					self.get("taxes")[i - 1].total + current_tax_amount, self.precision("total", tax)
				)

			tax.base_total = tax.total

			if self.payment_type == "Pay":
				if tax.currency != self.paid_to_account_currency:
					self.total_taxes_and_charges += flt(current_tax_amount / self.target_exchange_rate)
				else:
					self.total_taxes_and_charges += current_tax_amount
			elif self.payment_type == "Receive":
				if tax.currency != self.paid_from_account_currency:
					self.total_taxes_and_charges += flt(current_tax_amount / self.source_exchange_rate)
				else:
					self.total_taxes_and_charges += current_tax_amount

			self.base_total_taxes_and_charges += tax.base_tax_amount

		if self.get("taxes"):
			self.paid_amount_after_tax = self.get("taxes")[-1].base_total

	def get_current_tax_amount(self, tax):
		tax_rate = tax.rate

		# To set row_id by default as previous row.
		if tax.charge_type in ["On Previous Row Amount", "On Previous Row Total"]:
			if tax.idx == 1:
				frappe.throw(
					_(
						"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
					)
				)

			if not tax.row_id:
				tax.row_id = tax.idx - 1

		if tax.charge_type == "Actual":
			current_tax_amount = flt(tax.tax_amount, self.precision("tax_amount", tax))
		elif tax.charge_type == "On Paid Amount":
			current_tax_amount = (tax_rate / 100.0) * self.paid_amount_after_tax
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * self.get("taxes")[cint(tax.row_id) - 1].tax_amount

		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * self.get("taxes")[cint(tax.row_id) - 1].total

		return current_tax_amount

	def get_current_tax_fraction(self, tax):
		current_tax_fraction = 0

		if cint(tax.included_in_paid_amount):
			tax_rate = tax.rate

			if tax.charge_type == "On Paid Amount":
				current_tax_fraction = tax_rate / 100.0
			elif tax.charge_type == "On Previous Row Amount":
				current_tax_fraction = (tax_rate / 100.0) * self.get("taxes")[
					cint(tax.row_id) - 1
				].tax_fraction_for_current_item
			elif tax.charge_type == "On Previous Row Total":
				current_tax_fraction = (tax_rate / 100.0) * self.get("taxes")[
					cint(tax.row_id) - 1
				].grand_total_fraction_for_current_item

		if getattr(tax, "add_deduct_tax", None) and tax.add_deduct_tax == "Deduct":
			current_tax_fraction *= -1.0

		return current_tax_fraction


def validate_inclusive_tax(tax, doc):
	def _on_previous_row_error(row_range):
		throw(
			_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(
				tax.idx, row_range
			)
		)

	if cint(getattr(tax, "included_in_paid_amount", None)):
		if tax.charge_type == "Actual":
			# inclusive tax cannot be of type Actual
			throw(
				_("Charge of type 'Actual' in row {0} cannot be included in Item Rate or Paid Amount").format(
					tax.idx
				)
			)
		elif tax.charge_type == "On Previous Row Amount" and not cint(
			doc.get("taxes")[cint(tax.row_id) - 1].included_in_paid_amount
		):
			# referred row should also be inclusive
			_on_previous_row_error(tax.row_id)
		elif tax.charge_type == "On Previous Row Total" and not all(
			[cint(t.included_in_paid_amount for t in doc.get("taxes")[: cint(tax.row_id) - 1])]
		):
			# all rows about the referred tax should be inclusive
			_on_previous_row_error("1 - %d" % (cint(tax.row_id),))
		elif tax.get("category") == "Valuation":
			frappe.throw(_("Valuation type charges can not be marked as Inclusive"))


@frappe.whitelist()
def get_outstanding_reference_documents(args, validate=False):
	if isinstance(args, str):
		args = json.loads(args)

	if args.get("party_type") == "Member":
		return

	if not args.get("get_outstanding_invoices") and not args.get("get_orders_to_be_billed"):
		args["get_outstanding_invoices"] = True

	ple = qb.DocType("Payment Ledger Entry")
	common_filter = []
	accounting_dimensions_filter = []
	posting_and_due_date = []

	# confirm that Supplier is not blocked
	if args.get("party_type") == "Supplier":
		supplier_status = get_supplier_block_status(args["party"])
		if supplier_status["on_hold"]:
			if supplier_status["hold_type"] == "All":
				return []
			elif supplier_status["hold_type"] == "Payments":
				if (
					not supplier_status["release_date"]
					or getdate(nowdate()) <= supplier_status["release_date"]
				):
					return []

	party_account_currency = get_account_currency(args.get("party_account"))
	company_currency = frappe.get_cached_value("Company", args.get("company"), "default_currency")

	# Get positive outstanding sales /purchase invoices
	condition = ""
	if args.get("voucher_type") and args.get("voucher_no"):
		condition = " and voucher_type={} and voucher_no={}".format(
			frappe.db.escape(args["voucher_type"]), frappe.db.escape(args["voucher_no"])
		)
		common_filter.append(ple.voucher_type == args["voucher_type"])
		common_filter.append(ple.voucher_no == args["voucher_no"])

	# Add cost center condition
	if args.get("cost_center"):
		condition += " and cost_center='%s'" % args.get("cost_center")
		accounting_dimensions_filter.append(ple.cost_center == args.get("cost_center"))

	# dynamic dimension filters
	active_dimensions = get_dimensions()[0]
	for dim in active_dimensions:
		if args.get(dim.fieldname):
			condition += f" and {dim.fieldname}='{args.get(dim.fieldname)}'"
			accounting_dimensions_filter.append(ple[dim.fieldname] == args.get(dim.fieldname))

	date_fields_dict = {
		"posting_date": ["from_posting_date", "to_posting_date"],
		"due_date": ["from_due_date", "to_due_date"],
	}

	for fieldname, date_fields in date_fields_dict.items():
		if args.get(date_fields[0]) and args.get(date_fields[1]):
			condition += " and {} between '{}' and '{}'".format(
				fieldname, args.get(date_fields[0]), args.get(date_fields[1])
			)
			posting_and_due_date.append(ple[fieldname][args.get(date_fields[0]) : args.get(date_fields[1])])
		elif args.get(date_fields[0]):
			# if only from date is supplied
			condition += f" and {fieldname} >= '{args.get(date_fields[0])}'"
			posting_and_due_date.append(ple[fieldname].gte(args.get(date_fields[0])))
		elif args.get(date_fields[1]):
			# if only to date is supplied
			condition += f" and {fieldname} <= '{args.get(date_fields[1])}'"
			posting_and_due_date.append(ple[fieldname].lte(args.get(date_fields[1])))

	if args.get("company"):
		condition += " and company = {}".format(frappe.db.escape(args.get("company")))
		common_filter.append(ple.company == args.get("company"))

	outstanding_invoices = []
	negative_outstanding_invoices = []

	if args.get("book_advance_payments_in_separate_party_account"):
		party_account = get_party_account(args.get("party_type"), args.get("party"), args.get("company"))
	else:
		party_account = args.get("party_account")

	if args.get("get_outstanding_invoices"):
		outstanding_invoices = get_outstanding_invoices(
			args.get("party_type"),
			args.get("party"),
			[party_account],
			common_filter=common_filter,
			posting_date=posting_and_due_date,
			min_outstanding=args.get("outstanding_amt_greater_than"),
			max_outstanding=args.get("outstanding_amt_less_than"),
			accounting_dimensions=accounting_dimensions_filter,
			vouchers=args.get("vouchers") or None,
		)

		outstanding_invoices = split_invoices_based_on_payment_terms(
			outstanding_invoices, args.get("company")
		)

		for d in outstanding_invoices:
			d["exchange_rate"] = 1
			if party_account_currency != company_currency:
				if d.voucher_type in frappe.get_hooks("invoice_doctypes"):
					d["exchange_rate"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "conversion_rate")
				elif d.voucher_type == "Journal Entry":
					d["exchange_rate"] = get_exchange_rate(
						party_account_currency, company_currency, d.posting_date
					)
			if d.voucher_type in ("Purchase Invoice"):
				d["bill_no"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "bill_no")

		# Get negative outstanding sales /purchase invoices
		if args.get("party_type") != "Employee" and not args.get("voucher_no"):
			negative_outstanding_invoices = get_negative_outstanding_invoices(
				args.get("party_type"),
				args.get("party"),
				args.get("party_account"),
				party_account_currency,
				company_currency,
				condition=condition,
			)

	# Get all SO / PO which are not fully billed or against which full advance not paid
	orders_to_be_billed = []
	if args.get("get_orders_to_be_billed"):
		orders_to_be_billed = get_orders_to_be_billed(
			args.get("posting_date"),
			args.get("party_type"),
			args.get("party"),
			args.get("company"),
			party_account_currency,
			company_currency,
			filters=args,
		)

	data = negative_outstanding_invoices + outstanding_invoices + orders_to_be_billed

	if not data:
		if args.get("get_outstanding_invoices") and args.get("get_orders_to_be_billed"):
			ref_document_type = "invoices or orders"
		elif args.get("get_outstanding_invoices"):
			ref_document_type = "invoices"
		elif args.get("get_orders_to_be_billed"):
			ref_document_type = "orders"

		if not validate:
			frappe.msgprint(
				_(
					"No outstanding {0} found for the {1} {2} which qualify the filters you have specified."
				).format(
					_(ref_document_type), _(args.get("party_type")).lower(), frappe.bold(args.get("party"))
				)
			)

	return data


def split_invoices_based_on_payment_terms(outstanding_invoices, company) -> list:
	"""Split a list of invoices based on their payment terms."""
	exc_rates = get_currency_data(outstanding_invoices, company)

	outstanding_invoices_after_split = []
	for entry in outstanding_invoices:
		if entry.voucher_type in ["Sales Invoice", "Purchase Invoice"]:
			if payment_term_template := frappe.db.get_value(
				entry.voucher_type, entry.voucher_no, "payment_terms_template"
			):
				split_rows = get_split_invoice_rows(entry, payment_term_template, exc_rates)
				if not split_rows:
					continue

				if len(split_rows) > 1:
					frappe.msgprint(
						_("Splitting {0} {1} into {2} rows as per Payment Terms").format(
							_(entry.voucher_type), frappe.bold(entry.voucher_no), len(split_rows)
						),
						alert=True,
					)
				outstanding_invoices_after_split += split_rows
				continue

		# If not an invoice or no payment terms template, add as it is
		outstanding_invoices_after_split.append(entry)

	return outstanding_invoices_after_split


def get_currency_data(outstanding_invoices: list, company: str | None = None) -> dict:
	"""Get currency and conversion data for a list of invoices."""
	exc_rates = frappe._dict()
	company_currency = frappe.db.get_value("Company", company, "default_currency") if company else None

	for doctype in ["Sales Invoice", "Purchase Invoice"]:
		invoices = [x.voucher_no for x in outstanding_invoices if x.voucher_type == doctype]
		for x in frappe.db.get_all(
			doctype,
			filters={"name": ["in", invoices]},
			fields=["name", "currency", "conversion_rate", "party_account_currency"],
		):
			exc_rates[x.name] = frappe._dict(
				conversion_rate=x.conversion_rate,
				currency=x.currency,
				party_account_currency=x.party_account_currency,
				company_currency=company_currency,
			)

	return exc_rates


def get_split_invoice_rows(invoice: dict, payment_term_template: str, exc_rates: dict) -> list:
	"""Split invoice based on its payment schedule table."""
	split_rows = []
	allocate_payment_based_on_payment_terms = frappe.db.get_value(
		"Payment Terms Template", payment_term_template, "allocate_payment_based_on_payment_terms"
	)

	if not allocate_payment_based_on_payment_terms:
		return [invoice]

	payment_schedule = frappe.get_all(
		"Payment Schedule", filters={"parent": invoice.voucher_no}, fields=["*"], order_by="due_date"
	)
	for payment_term in payment_schedule:
		if not payment_term.outstanding > 0.1:
			continue

		doc_details = exc_rates.get(payment_term.parent, None)
		is_multi_currency_acc = (doc_details.currency != doc_details.company_currency) and (
			doc_details.party_account_currency != doc_details.company_currency
		)
		payment_term_outstanding = flt(payment_term.outstanding)
		if not is_multi_currency_acc:
			payment_term_outstanding = doc_details.conversion_rate * flt(payment_term.outstanding)

		split_rows.append(
			frappe._dict(
				{
					"due_date": invoice.due_date,
					"currency": invoice.currency,
					"voucher_no": invoice.voucher_no,
					"voucher_type": invoice.voucher_type,
					"posting_date": invoice.posting_date,
					"invoice_amount": flt(invoice.invoice_amount),
					"outstanding_amount": payment_term_outstanding
					if payment_term_outstanding
					else invoice.outstanding_amount,
					"payment_term_outstanding": payment_term_outstanding,
					"payment_amount": payment_term.payment_amount,
					"payment_term": payment_term.payment_term,
				}
			)
		)

	return split_rows


def get_orders_to_be_billed(
	posting_date,
	party_type,
	party,
	company,
	party_account_currency,
	company_currency,
	cost_center=None,
	filters=None,
):
	voucher_type = None
	if party_type == "Customer":
		voucher_type = "Sales Order"
	elif party_type == "Supplier":
		voucher_type = "Purchase Order"

	if not voucher_type:
		return []

	# Add cost center condition
	doc = frappe.get_doc({"doctype": voucher_type})
	condition = ""
	if doc and hasattr(doc, "cost_center") and doc.cost_center:
		condition = " and cost_center='%s'" % cost_center

	# dynamic dimension filters
	active_dimensions = get_dimensions()[0]
	for dim in active_dimensions:
		if filters.get(dim.fieldname):
			condition += f" and {dim.fieldname}='{filters.get(dim.fieldname)}'"

	if party_account_currency == company_currency:
		grand_total_field = "base_grand_total"
		rounded_total_field = "base_rounded_total"
	else:
		grand_total_field = "grand_total"
		rounded_total_field = "rounded_total"

	orders = frappe.db.sql(
		"""
		select
			name as voucher_no,
			if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) as invoice_amount,
			(if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) - advance_paid) as outstanding_amount,
			transaction_date as posting_date
		from
			`tab{voucher_type}`
		where
			{party_type} = %s
			and docstatus = 1
			and company = %s
			and status != "Closed"
			and if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) > advance_paid
			and abs(100 - per_billed) > 0.01
			{condition}
		order by
			transaction_date, name
	""".format(
			**{
				"rounded_total_field": rounded_total_field,
				"grand_total_field": grand_total_field,
				"voucher_type": voucher_type,
				"party_type": scrub(party_type),
				"condition": condition,
			}
		),
		(party, company),
		as_dict=True,
	)

	order_list = []
	for d in orders:
		if (
			filters
			and filters.get("outstanding_amt_greater_than")
			and filters.get("outstanding_amt_less_than")
			and not (
				flt(filters.get("outstanding_amt_greater_than"))
				<= flt(d.outstanding_amount)
				<= flt(filters.get("outstanding_amt_less_than"))
			)
		):
			continue

		d["voucher_type"] = voucher_type
		# This assumes that the exchange rate required is the one in the SO
		d["exchange_rate"] = get_exchange_rate(party_account_currency, company_currency, posting_date)
		order_list.append(d)

	return order_list


def get_negative_outstanding_invoices(
	party_type,
	party,
	party_account,
	party_account_currency,
	company_currency,
	cost_center=None,
	condition=None,
):
	if party_type not in ["Customer", "Supplier"]:
		return []
	voucher_type = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
	account = "debit_to" if voucher_type == "Sales Invoice" else "credit_to"
	supplier_condition = ""
	if voucher_type == "Purchase Invoice":
		supplier_condition = "and (release_date is null or release_date <= CURRENT_DATE)"
	if party_account_currency == company_currency:
		grand_total_field = "base_grand_total"
		rounded_total_field = "base_rounded_total"
	else:
		grand_total_field = "grand_total"
		rounded_total_field = "rounded_total"

	return frappe.db.sql(
		"""
		select
			"{voucher_type}" as voucher_type, name as voucher_no, {account} as account,
			if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) as invoice_amount,
			outstanding_amount, posting_date,
			due_date, conversion_rate as exchange_rate
		from
			`tab{voucher_type}`
		where
			{party_type} = %s and {party_account} = %s and docstatus = 1 and
			outstanding_amount < 0
			{supplier_condition}
			{condition}
		order by
			posting_date, name
		""".format(
			**{
				"supplier_condition": supplier_condition,
				"condition": condition,
				"rounded_total_field": rounded_total_field,
				"grand_total_field": grand_total_field,
				"voucher_type": voucher_type,
				"party_type": scrub(party_type),
				"party_account": "debit_to" if party_type == "Customer" else "credit_to",
				"cost_center": cost_center,
				"account": account,
			}
		),
		(party, party_account),
		as_dict=True,
	)


@frappe.whitelist()
def get_party_details(company, party_type, party, date, cost_center=None):
	bank_account = ""
	party_bank_account = ""

	if not frappe.db.exists(party_type, party):
		frappe.throw(_("{0} {1} does not exist").format(_(party_type), party))

	party_account = get_party_account(party_type, party, company)
	account_currency = get_account_currency(party_account)
	account_balance = get_balance_on(party_account, date, cost_center=cost_center)
	_party_name = "title" if party_type == "Shareholder" else party_type.lower() + "_name"
	party_name = frappe.db.get_value(party_type, party, _party_name)
	party_balance = get_balance_on(party_type=party_type, party=party, cost_center=cost_center)
	if party_type in ["Customer", "Supplier"]:
		party_bank_account = get_party_bank_account(party_type, party)
		bank_account = get_default_company_bank_account(company, party_type, party)

	return {
		"party_account": party_account,
		"party_name": party_name,
		"party_account_currency": account_currency,
		"party_balance": party_balance,
		"account_balance": account_balance,
		"party_bank_account": party_bank_account,
		"bank_account": bank_account,
	}


@frappe.whitelist()
def get_account_details(account, date, cost_center=None):
	frappe.has_permission("Payment Entry", throw=True)

	# to check if the passed account is accessible under reference doctype Payment Entry
	account_list = frappe.get_list("Account", {"name": account}, reference_doctype="Payment Entry", limit=1)

	# There might be some user permissions which will allow account under certain doctypes
	# except for Payment Entry, only in such case we should throw permission error
	if not account_list:
		frappe.throw(_("Account: {0} is not permitted under Payment Entry").format(account))

	account_balance = get_balance_on(account, date, cost_center=cost_center, ignore_account_permission=True)

	return frappe._dict(
		{
			"account_currency": get_account_currency(account),
			"account_balance": account_balance,
			"account_type": frappe.get_cached_value("Account", account, "account_type"),
		}
	)


@frappe.whitelist()
def get_company_defaults(company):
	fields = ["write_off_account", "exchange_gain_loss_account", "cost_center"]
	return frappe.get_cached_value("Company", company, fields, as_dict=1)


def get_outstanding_on_journal_entry(voucher_no, party_type, party):
	ple = frappe.qb.DocType("Payment Ledger Entry")

	outstanding = (
		frappe.qb.from_(ple)
		.select(Sum(ple.amount_in_account_currency))
		.where(
			(ple.against_voucher_no == voucher_no)
			& (ple.party_type == party_type)
			& (ple.party == party)
			& (ple.delinked == 0)
		)
	).run()

	outstanding_amount = outstanding[0][0] if outstanding else 0

	total = (
		frappe.qb.from_(ple)
		.select(Sum(ple.amount_in_account_currency))
		.where(
			(ple.voucher_no == voucher_no)
			& (ple.party_type == party_type)
			& (ple.party == party)
			& (ple.delinked == 0)
		)
	).run()

	total_amount = total[0][0] if total else 0

	return outstanding_amount, total_amount


@frappe.whitelist()
def get_reference_details(
	reference_doctype, reference_name, party_account_currency, party_type=None, party=None
):
	total_amount = outstanding_amount = exchange_rate = account = None

	ref_doc = frappe.get_doc(reference_doctype, reference_name)
	company_currency = ref_doc.get("company_currency") or erpnext.get_company_currency(ref_doc.company)

	# Only applies for Reverse Payment Entries
	account_type = None
	payment_type = None

	if reference_doctype == "Dunning":
		total_amount = outstanding_amount = ref_doc.get("dunning_amount")
		exchange_rate = 1

	elif reference_doctype == "Journal Entry" and ref_doc.docstatus == 1:
		if ref_doc.multi_currency:
			exchange_rate = get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)
		else:
			exchange_rate = 1
			outstanding_amount, total_amount = get_outstanding_on_journal_entry(
				reference_name, party_type, party
			)

	elif reference_doctype == "Payment Entry":
		if reverse_payment_details := frappe.db.get_all(
			"Payment Entry",
			filters={"name": reference_name},
			fields=["payment_type", "party_type"],
		)[0]:
			payment_type = reverse_payment_details.payment_type
			account_type = frappe.db.get_value(
				"Party Type", reverse_payment_details.party_type, "account_type"
			)
		exchange_rate = 1

	elif reference_doctype != "Journal Entry":
		if not total_amount:
			if party_account_currency == company_currency:
				# for handling cases that don't have multi-currency (base field)
				total_amount = (
					ref_doc.get("base_rounded_total")
					or ref_doc.get("rounded_total")
					or ref_doc.get("base_grand_total")
					or ref_doc.get("grand_total")
				)
				exchange_rate = 1
			else:
				total_amount = ref_doc.get("rounded_total") or ref_doc.get("grand_total")
		if not exchange_rate:
			# Get the exchange rate from the original ref doc
			# or get it based on the posting date of the ref doc.
			exchange_rate = ref_doc.get("conversion_rate") or get_exchange_rate(
				party_account_currency, company_currency, ref_doc.posting_date
			)

		if reference_doctype in ("Sales Invoice", "Purchase Invoice"):
			outstanding_amount = ref_doc.get("outstanding_amount")
			account = (
				ref_doc.get("debit_to") if reference_doctype == "Sales Invoice" else ref_doc.get("credit_to")
			)
		else:
			outstanding_amount = flt(total_amount) - flt(ref_doc.get("advance_paid"))

		if reference_doctype in ["Sales Order", "Purchase Order"]:
			party_type = "Customer" if reference_doctype == "Sales Order" else "Supplier"
			party_field = "customer" if reference_doctype == "Sales Order" else "supplier"
			party = ref_doc.get(party_field)
			account = get_party_account(party_type, party, ref_doc.company)
	else:
		# Get the exchange rate based on the posting date of the ref doc.
		exchange_rate = get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)

	res = frappe._dict(
		{
			"due_date": ref_doc.get("due_date"),
			"total_amount": flt(total_amount),
			"outstanding_amount": flt(outstanding_amount),
			"exchange_rate": flt(exchange_rate),
			"bill_no": ref_doc.get("bill_no"),
			"account_type": account_type,
			"payment_type": payment_type,
		}
	)
	if account:
		res.update({"account": account})
	return res


@frappe.whitelist()
def get_payment_entry(
	dt,
	dn,
	party_amount=None,
	bank_account=None,
	bank_amount=None,
	party_type=None,
	payment_type=None,
	reference_date=None,
):
	doc = frappe.get_doc(dt, dn)
	over_billing_allowance = frappe.db.get_single_value("Accounts Settings", "over_billing_allowance")
	if dt in ("Sales Order", "Purchase Order") and flt(doc.per_billed, 2) >= (100.0 + over_billing_allowance):
		frappe.throw(_("Can only make payment against unbilled {0}").format(_(dt)))

	if not party_type:
		party_type = set_party_type(dt)

	party_account = set_party_account(dt, dn, doc, party_type)
	party_account_currency = set_party_account_currency(dt, party_account, doc)

	if not payment_type:
		payment_type = set_payment_type(dt, doc)

	grand_total, outstanding_amount = set_grand_total_and_outstanding_amount(
		party_amount, dt, party_account_currency, doc
	)

	# bank or cash
	bank = get_bank_cash_account(doc, bank_account)

	# if default bank or cash account is not set in company master and party has default company bank account, fetch it
	if party_type in ["Customer", "Supplier"] and not bank:
		party_bank_account = get_party_bank_account(party_type, doc.get(scrub(party_type)))
		if party_bank_account:
			account = frappe.db.get_value("Bank Account", party_bank_account, "account")
			bank = get_bank_cash_account(doc, account)

	paid_amount, received_amount = set_paid_amount_and_received_amount(
		dt, party_account_currency, bank, outstanding_amount, payment_type, bank_amount, doc
	)

	reference_date = getdate(reference_date)
	paid_amount, received_amount, discount_amount, valid_discounts = apply_early_payment_discount(
		paid_amount, received_amount, doc, party_account_currency, reference_date
	)

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = payment_type
	pe.company = doc.company
	pe.cost_center = doc.get("cost_center")
	pe.posting_date = nowdate()
	pe.reference_date = reference_date
	pe.mode_of_payment = doc.get("mode_of_payment")
	pe.party_type = party_type
	pe.party = doc.get(scrub(party_type))
	pe.contact_person = doc.get("contact_person")
	pe.contact_email = doc.get("contact_email")
	pe.ensure_supplier_is_not_blocked()

	pe.paid_from = party_account if payment_type == "Receive" else bank.account
	pe.paid_to = party_account if payment_type == "Pay" else bank.account
	pe.paid_from_account_currency = (
		party_account_currency if payment_type == "Receive" else bank.account_currency
	)
	pe.paid_to_account_currency = party_account_currency if payment_type == "Pay" else bank.account_currency
	pe.paid_amount = paid_amount
	pe.received_amount = received_amount
	pe.letter_head = doc.get("letter_head")

	if dt in ["Purchase Order", "Sales Order", "Sales Invoice", "Purchase Invoice"]:
		pe.project = doc.get("project") or reduce(
			lambda prev, cur: prev or cur, [x.get("project") for x in doc.get("items")], None
		)  # get first non-empty project from items

	if pe.party_type in ["Customer", "Supplier"]:
		bank_account = get_party_bank_account(pe.party_type, pe.party)
		pe.set("bank_account", bank_account)
		pe.set_bank_account_data()

	# only Purchase Invoice can be blocked individually
	if doc.doctype == "Purchase Invoice" and doc.invoice_is_blocked():
		frappe.msgprint(_("{0} is on hold till {1}").format(doc.name, doc.release_date))
	else:
		if doc.doctype in (
			"Sales Invoice",
			"Purchase Invoice",
			"Purchase Order",
			"Sales Order",
		) and frappe.get_cached_value(
			"Payment Terms Template",
			doc.payment_terms_template,
			"allocate_payment_based_on_payment_terms",
		):
			for reference in get_reference_as_per_payment_terms(
				doc.payment_schedule, dt, dn, doc, grand_total, outstanding_amount, party_account_currency
			):
				pe.append("references", reference)
		else:
			if dt == "Dunning":
				for overdue_payment in doc.overdue_payments:
					pe.append(
						"references",
						{
							"reference_doctype": "Sales Invoice",
							"reference_name": overdue_payment.sales_invoice,
							"payment_term": overdue_payment.payment_term,
							"due_date": overdue_payment.due_date,
							"total_amount": overdue_payment.outstanding,
							"outstanding_amount": overdue_payment.outstanding,
							"allocated_amount": overdue_payment.outstanding,
						},
					)

				pe.append(
					"deductions",
					{
						"account": doc.income_account,
						"cost_center": doc.cost_center,
						"amount": -1 * doc.dunning_amount,
						"description": _("Interest and/or dunning fee"),
					},
				)
			else:
				pe.append(
					"references",
					{
						"reference_doctype": dt,
						"reference_name": dn,
						"bill_no": doc.get("bill_no"),
						"due_date": doc.get("due_date"),
						"total_amount": grand_total,
						"outstanding_amount": outstanding_amount,
						"allocated_amount": outstanding_amount,
					},
				)

	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.set_missing_ref_details()

	update_accounting_dimensions(pe, doc)

	if party_account and bank:
		pe.set_exchange_rate(ref_doc=doc)
		pe.set_amounts()

		if discount_amount:
			base_total_discount_loss = 0
			if frappe.db.get_single_value("Accounts Settings", "book_tax_discount_loss"):
				base_total_discount_loss = split_early_payment_discount_loss(pe, doc, valid_discounts)

			set_pending_discount_loss(
				pe, doc, discount_amount, base_total_discount_loss, party_account_currency
			)

		pe.set_difference_amount()

	return pe


def update_accounting_dimensions(pe, doc):
	"""
	Updates accounting dimensions in Payment Entry based on the accounting dimensions in the reference document
	"""
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		get_accounting_dimensions,
	)

	for dimension in get_accounting_dimensions():
		pe.set(dimension, doc.get(dimension))


def get_bank_cash_account(doc, bank_account):
	bank = get_default_bank_cash_account(
		doc.company, "Bank", mode_of_payment=doc.get("mode_of_payment"), account=bank_account
	)

	if not bank:
		bank = get_default_bank_cash_account(
			doc.company, "Cash", mode_of_payment=doc.get("mode_of_payment"), account=bank_account
		)

	return bank


def set_party_type(dt):
	if dt in ("Sales Invoice", "Sales Order", "Dunning"):
		party_type = "Customer"
	elif dt in ("Purchase Invoice", "Purchase Order"):
		party_type = "Supplier"
	return party_type


def set_party_account(dt, dn, doc, party_type):
	if dt == "Sales Invoice":
		party_account = get_party_account_based_on_invoice_discounting(dn) or doc.debit_to
	elif dt == "Purchase Invoice":
		party_account = doc.credit_to
	else:
		party_account = get_party_account(party_type, doc.get(party_type.lower()), doc.company)
	return party_account


def set_party_account_currency(dt, party_account, doc):
	if dt not in ("Sales Invoice", "Purchase Invoice"):
		party_account_currency = get_account_currency(party_account)
	else:
		party_account_currency = doc.get("party_account_currency") or get_account_currency(party_account)
	return party_account_currency


def set_payment_type(dt, doc):
	if (
		(dt == "Sales Order" or (dt == "Sales Invoice" and doc.outstanding_amount > 0))
		or (dt == "Purchase Invoice" and doc.outstanding_amount < 0)
		or dt == "Dunning"
	):
		payment_type = "Receive"
	else:
		payment_type = "Pay"
	return payment_type


def set_grand_total_and_outstanding_amount(party_amount, dt, party_account_currency, doc):
	grand_total = outstanding_amount = 0
	if party_amount:
		grand_total = outstanding_amount = party_amount
	elif dt in ("Sales Invoice", "Purchase Invoice"):
		if party_account_currency == doc.company_currency:
			grand_total = doc.base_rounded_total or doc.base_grand_total
		else:
			grand_total = doc.rounded_total or doc.grand_total
		outstanding_amount = doc.outstanding_amount
	elif dt == "Dunning":
		grand_total = doc.grand_total
		outstanding_amount = doc.grand_total
	else:
		if party_account_currency == doc.company_currency:
			grand_total = flt(doc.get("base_rounded_total") or doc.get("base_grand_total"))
		else:
			grand_total = flt(doc.get("rounded_total") or doc.get("grand_total"))
		outstanding_amount = doc.get("outstanding_amount") or (grand_total - flt(doc.advance_paid))
	return grand_total, outstanding_amount


def set_paid_amount_and_received_amount(
	dt, party_account_currency, bank, outstanding_amount, payment_type, bank_amount, doc
):
	paid_amount = received_amount = 0
	if party_account_currency == bank.account_currency:
		paid_amount = received_amount = abs(outstanding_amount)
	else:
		company_currency = frappe.get_cached_value("Company", doc.get("company"), "default_currency")
		if payment_type == "Receive":
			paid_amount = abs(outstanding_amount)
			if bank_amount:
				received_amount = bank_amount
			else:
				if bank and company_currency != bank.account_currency:
					received_amount = paid_amount / doc.get("conversion_rate", 1)
				else:
					received_amount = paid_amount * doc.get("conversion_rate", 1)
		else:
			received_amount = abs(outstanding_amount)
			if bank_amount:
				paid_amount = bank_amount
			else:
				if bank and company_currency != bank.account_currency:
					paid_amount = received_amount / doc.get("conversion_rate", 1)
				else:
					# if party account currency and bank currency is different then populate paid amount as well
					paid_amount = received_amount * doc.get("conversion_rate", 1)

	return paid_amount, received_amount


def apply_early_payment_discount(paid_amount, received_amount, doc, party_account_currency, reference_date):
	total_discount = 0
	valid_discounts = []
	eligible_for_payments = ["Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice"]
	has_payment_schedule = hasattr(doc, "payment_schedule") and doc.payment_schedule
	is_multi_currency = party_account_currency != doc.company_currency

	if doc.doctype in eligible_for_payments and has_payment_schedule:
		for term in doc.payment_schedule:
			if not term.discounted_amount and term.discount and reference_date <= term.discount_date:
				if term.discount_type == "Percentage":
					grand_total = doc.get("grand_total") if is_multi_currency else doc.get("base_grand_total")
					discount_amount = flt(grand_total) * (term.discount / 100)
				else:
					discount_amount = term.discount

				# if accounting is done in the same currency, paid_amount = received_amount
				conversion_rate = doc.get("conversion_rate", 1) if is_multi_currency else 1
				discount_amount_in_foreign_currency = discount_amount * conversion_rate

				if doc.doctype == "Sales Invoice":
					paid_amount -= discount_amount
					received_amount -= discount_amount_in_foreign_currency
				else:
					received_amount -= discount_amount
					paid_amount -= discount_amount_in_foreign_currency

				valid_discounts.append({"type": term.discount_type, "discount": term.discount})
				total_discount += discount_amount

		if total_discount:
			currency = doc.get("currency") if is_multi_currency else doc.company_currency
			money = frappe.utils.fmt_money(total_discount, currency=currency)
			frappe.msgprint(_("Discount of {} applied as per Payment Term").format(money), alert=1)

	return paid_amount, received_amount, total_discount, valid_discounts


def set_pending_discount_loss(pe, doc, discount_amount, base_total_discount_loss, party_account_currency):
	# If multi-currency, get base discount amount to adjust with base currency deductions/losses
	if party_account_currency != doc.company_currency:
		discount_amount = discount_amount * doc.get("conversion_rate", 1)

	# Avoid considering miniscule losses
	discount_amount = flt(discount_amount - base_total_discount_loss, doc.precision("grand_total"))

	# Set base discount amount (discount loss/pending rounding loss) in deductions
	if discount_amount > 0.0:
		positive_negative = -1 if pe.payment_type == "Pay" else 1

		# If tax loss booking is enabled, pending loss will be rounding loss.
		# Otherwise it will be the total discount loss.
		book_tax_loss = frappe.db.get_single_value("Accounts Settings", "book_tax_discount_loss")
		account_type = "round_off_account" if book_tax_loss else "default_discount_account"

		pe.set_gain_or_loss(
			account_details={
				"account": frappe.get_cached_value("Company", pe.company, account_type),
				"cost_center": pe.cost_center
				or frappe.get_cached_value("Company", pe.company, "cost_center"),
				"amount": discount_amount * positive_negative,
			}
		)


def split_early_payment_discount_loss(pe, doc, valid_discounts) -> float:
	"""Split early payment discount into Income Loss & Tax Loss."""
	total_discount_percent = get_total_discount_percent(doc, valid_discounts)

	if not total_discount_percent:
		return 0.0

	base_loss_on_income = add_income_discount_loss(pe, doc, total_discount_percent)
	base_loss_on_taxes = add_tax_discount_loss(pe, doc, total_discount_percent)

	# Round off total loss rather than individual losses to reduce rounding error
	return flt(base_loss_on_income + base_loss_on_taxes, doc.precision("grand_total"))


def get_total_discount_percent(doc, valid_discounts) -> float:
	"""Get total percentage and amount discount applied as a percentage."""
	total_discount_percent = (
		sum(discount.get("discount") for discount in valid_discounts if discount.get("type") == "Percentage")
		or 0.0
	)

	# Operate in percentages only as it makes the income & tax split easier
	total_discount_amount = (
		sum(discount.get("discount") for discount in valid_discounts if discount.get("type") == "Amount")
		or 0.0
	)

	if total_discount_amount:
		discount_percentage = (total_discount_amount / doc.get("grand_total")) * 100
		total_discount_percent += discount_percentage
		return total_discount_percent

	return total_discount_percent


def add_income_discount_loss(pe, doc, total_discount_percent) -> float:
	"""Add loss on income discount in base currency."""
	precision = doc.precision("total")
	base_loss_on_income = doc.get("base_total") * (total_discount_percent / 100)

	pe.append(
		"deductions",
		{
			"account": frappe.get_cached_value("Company", pe.company, "default_discount_account"),
			"cost_center": pe.cost_center or frappe.get_cached_value("Company", pe.company, "cost_center"),
			"amount": flt(base_loss_on_income, precision),
		},
	)

	return base_loss_on_income  # Return loss without rounding


def add_tax_discount_loss(pe, doc, total_discount_percentage) -> float:
	"""Add loss on tax discount in base currency."""
	tax_discount_loss = {}
	base_total_tax_loss = 0
	precision = doc.precision("tax_amount_after_discount_amount", "taxes")

	# The same account head could be used more than once
	for tax in doc.get("taxes", []):
		base_tax_loss = tax.get("base_tax_amount_after_discount_amount") * (total_discount_percentage / 100)

		account = tax.get("account_head")
		if not tax_discount_loss.get(account):
			tax_discount_loss[account] = base_tax_loss
		else:
			tax_discount_loss[account] += base_tax_loss

	for account, loss in tax_discount_loss.items():
		base_total_tax_loss += loss
		if loss == 0.0:
			continue

		pe.append(
			"deductions",
			{
				"account": account,
				"cost_center": pe.cost_center
				or frappe.get_cached_value("Company", pe.company, "cost_center"),
				"amount": flt(loss, precision),
			},
		)

	return base_total_tax_loss  # Return loss without rounding


def get_reference_as_per_payment_terms(
	payment_schedule, dt, dn, doc, grand_total, outstanding_amount, party_account_currency
):
	references = []
	is_multi_currency_acc = (doc.currency != doc.company_currency) and (
		party_account_currency != doc.company_currency
	)

	for payment_term in payment_schedule:
		payment_term_outstanding = flt(
			payment_term.payment_amount - payment_term.paid_amount, payment_term.precision("payment_amount")
		)
		if not is_multi_currency_acc:
			# If accounting is done in company currency for multi-currency transaction
			payment_term_outstanding = flt(
				payment_term_outstanding * doc.get("conversion_rate"),
				payment_term.precision("payment_amount"),
			)

		if payment_term_outstanding:
			references.append(
				{
					"reference_doctype": dt,
					"reference_name": dn,
					"bill_no": doc.get("bill_no"),
					"due_date": doc.get("due_date"),
					"total_amount": grand_total,
					"outstanding_amount": outstanding_amount,
					"payment_term_outstanding": payment_term_outstanding,
					"payment_term": payment_term.payment_term,
					"allocated_amount": payment_term_outstanding,
				}
			)

	return references


def get_paid_amount(dt, dn, party_type, party, account, due_date):
	if party_type == "Customer":
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	paid_amount = frappe.db.sql(
		f"""
		select ifnull(sum({dr_or_cr}), 0) as paid_amount
		from `tabGL Entry`
		where against_voucher_type = %s
			and against_voucher = %s
			and party_type = %s
			and party = %s
			and account = %s
			and due_date = %s
			and {dr_or_cr} > 0
	""",
		(dt, dn, party_type, party, account, due_date),
	)

	return paid_amount[0][0] if paid_amount else 0


@frappe.whitelist()
def get_party_and_account_balance(
	company, date, paid_from=None, paid_to=None, ptype=None, pty=None, cost_center=None
):
	return frappe._dict(
		{
			"party_balance": get_balance_on(party_type=ptype, party=pty, cost_center=cost_center),
			"paid_from_account_balance": get_balance_on(paid_from, date, cost_center=cost_center),
			"paid_to_account_balance": get_balance_on(paid_to, date=date, cost_center=cost_center),
		}
	)


@frappe.whitelist()
def make_payment_order(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def set_missing_values(source, target):
		target.payment_order_type = "Payment Entry"
		target.append(
			"references",
			dict(
				reference_doctype="Payment Entry",
				reference_name=source.name,
				bank_account=source.party_bank_account,
				amount=source.paid_amount,
				account=source.paid_to,
				supplier=source.party,
				mode_of_payment=source.mode_of_payment,
			),
		)

	doclist = get_mapped_doc(
		"Payment Entry",
		source_name,
		{
			"Payment Entry": {
				"doctype": "Payment Order",
				"validation": {"docstatus": ["=", 1]},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@erpnext.allow_regional
def add_regional_gl_entries(gl_entries, doc):
	return
