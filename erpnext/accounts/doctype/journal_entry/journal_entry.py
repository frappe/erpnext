# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from datetime import date

import frappe
from frappe import _, msgprint, scrub
from frappe.core.doctype.submission_queue.submission_queue import queue_submission
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import comma_and, cstr, flt, fmt_money, formatdate, get_link_to_form, nowdate

import erpnext
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import (
	get_party_account_based_on_invoice_discounting,
)

# Re-exported so existing call paths (including custom apps) referencing
# erpnext.accounts.doctype.journal_entry.journal_entry.<fn> keep working.
from erpnext.accounts.doctype.journal_entry.mapper import (
	get_payment_entry_against_invoice,
	get_payment_entry_against_order,
)
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	validate_docs_for_deferred_accounting,
	validate_docs_for_voucher_types,
)
from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import JournalTaxWithholding
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import (
	cancel_exchange_gain_loss_journal,
	get_account_currency,
	get_balance_on,
	get_stock_accounts,
	get_stock_and_account_balance,
)
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.setup.utils import get_exchange_rate as _get_exchange_rate


class StockAccountInvalidTransaction(frappe.ValidationError):
	pass


class JournalEntry(AccountsController):
	"""Double-entry accounting voucher for manual and system-generated postings.

	Besides plain journal entries it also backs depreciation, asset disposal,
	exchange gain/loss, deferred revenue/expense, inter-company and periodic
	accounting entries: it validates the account rows (party, references,
	currency) and posts the corresponding GL entries on submit.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.journal_entry_account.journal_entry_account import JournalEntryAccount
		from erpnext.accounts.doctype.tax_withholding_entry.tax_withholding_entry import TaxWithholdingEntry

		accounts: DF.Table[JournalEntryAccount]
		amended_from: DF.Link | None
		apply_tds: DF.Check
		auto_repeat: DF.Link | None
		bill_date: DF.Date | None
		bill_no: DF.Data | None
		cheque_date: DF.Date | None
		cheque_no: DF.Data | None
		clearance_date: DF.Date | None
		company: DF.Link
		custom_remark: DF.Check
		difference: DF.Currency
		due_date: DF.Date | None
		finance_book: DF.Link | None
		for_all_stock_asset_accounts: DF.Check
		from_template: DF.Link | None
		ignore_tax_withholding_threshold: DF.Check
		inter_company_journal_entry_reference: DF.Link | None
		is_opening: DF.Literal["No", "Yes"]
		is_system_generated: DF.Check
		letter_head: DF.Link | None
		mode_of_payment: DF.Link | None
		multi_currency: DF.Check
		naming_series: DF.Literal["ACC-JV-.YYYY.-"]
		override_tax_withholding_entries: DF.Check
		party_not_required: DF.Check
		pay_to_recd_from: DF.Data | None
		payment_order: DF.Link | None
		periodic_entry_difference_account: DF.Link | None
		posting_date: DF.Date
		process_deferred_accounting: DF.Link | None
		remark: DF.SmallText | None
		reversal_of: DF.Link | None
		select_print_heading: DF.Link | None
		stock_asset_account: DF.Link | None
		stock_entry: DF.Link | None
		tax_withholding_category: DF.Link | None
		tax_withholding_entries: DF.Table[TaxWithholdingEntry]
		tax_withholding_group: DF.Link | None
		title: DF.Data | None
		total_amount: DF.Currency
		total_amount_currency: DF.Link | None
		total_amount_in_words: DF.Data | None
		total_credit: DF.Currency
		total_debit: DF.Currency
		user_remark: DF.SmallText | None
		voucher_type: DF.Literal[
			"Journal Entry",
			"Inter Company Journal Entry",
			"Bank Entry",
			"Cash Entry",
			"Credit Card Entry",
			"Debit Note",
			"Credit Note",
			"Contra Entry",
			"Excise Entry",
			"Write Off Entry",
			"Opening Entry",
			"Depreciation Entry",
			"Asset Disposal",
			"Periodic Accounting Entry",
			"Exchange Rate Revaluation",
			"Exchange Gain Or Loss",
			"Deferred Revenue",
			"Deferred Expense",
		]
		write_off_amount: DF.Currency
		write_off_based_on: DF.Literal["Accounts Receivable", "Accounts Payable"]
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def validate(self):
		"""Validate the account rows (party, references, currency, stock) and build derived fields."""
		from erpnext.accounts.doctype.journal_entry.services.asset_service import AssetService
		from erpnext.accounts.doctype.journal_entry.services.reference_validator import (
			JournalEntryReferenceValidator,
		)

		if self.voucher_type == "Opening Entry":
			self.is_opening = "Yes"

		if not self.is_opening:
			self.is_opening = "No"

		self.clearance_date = None

		self.validate_party()
		self.validate_entries_for_advance()
		self.validate_multi_currency()
		self.set_amounts_in_company_currency()
		self.validate_debit_credit_amount()
		self.set_total_debit_credit()

		if not frappe.flags.is_reverse_depr_entry:
			self.validate_against_jv()
			self.validate_stock_accounts()

		JournalEntryReferenceValidator(self).validate()
		if self.docstatus == 0:
			self.set_against_account()
		self.create_remarks()
		self.set_print_format_fields()
		self.validate_credit_debit_note()
		self.validate_empty_accounts_table()
		self.validate_inter_company_accounts()
		AssetService(self).validate_depr_account_and_depr_entry_voucher_type()
		self.validate_company_in_accounting_dimension()
		self.validate_advance_accounts()

		JournalTaxWithholding(self).on_validate()

		if self.is_new() or not self.title:
			self.title = self.get_title()

	def validate_advance_accounts(self):
		journal_accounts = set([x.account for x in self.accounts])
		advance_accounts = set()
		advance_accounts.add(
			frappe.get_cached_value("Company", self.company, "default_advance_received_account")
		)
		advance_accounts.add(frappe.get_cached_value("Company", self.company, "default_advance_paid_account"))
		if advance_accounts_used := journal_accounts & advance_accounts:
			frappe.msgprint(
				_(
					"Making Journal Entries against advance accounts: {0} is not recommended. These Journals won't be available for Reconciliation."
				).format(frappe.bold(comma_and(advance_accounts_used)))
			)

	def validate_for_repost(self):
		validate_docs_for_voucher_types(["Journal Entry"])
		validate_docs_for_deferred_accounting([self.name], [])

	def submit(self):
		"""Submit inline, or queue submission in the background for large entries."""
		if len(self.accounts) > 100 and not self.meta.queue_in_background:
			queue_submission(self, "_submit")
		else:
			return self._submit()

	def before_cancel(self):
		"""Block cancellation when a submitted Asset Value Adjustment is linked to this entry."""
		from erpnext.accounts.doctype.journal_entry.services.asset_service import AssetService

		AssetService(self).has_asset_adjustment_entry()

	def cancel(self):
		"""Cancel inline, or queue cancellation in the background for large entries."""
		if len(self.accounts) > 100:
			queue_submission(self, "_cancel")
		else:
			return self._cancel()

	def before_submit(self):
		"""Ensure total debit equals total credit before submission (skipped on data import)."""
		# Do not validate while importing via data import
		if not frappe.flags.in_import:
			self.validate_total_debit_and_credit()

	def on_submit(self):
		"""Post GL entries and propagate the submission to assets, inter-company JE and invoice discounting."""
		from erpnext.accounts.doctype.journal_entry.services.asset_service import AssetService

		self.validate_cheque_info()
		self.make_gl_entries()
		self.check_credit_limit()
		AssetService(self).update_asset_value()
		self.update_inter_company_jv()
		self.update_invoice_discounting()
		JournalTaxWithholding(self).on_submit()

	@frappe.whitelist()
	def get_balance_for_periodic_accounting(self) -> None:
		"""Rebuild the entry rows from the stock-vs-ledger difference of each stock account."""
		self.validate_company_for_periodic_accounting()

		self.set("accounts", [])
		for account in self.get_stock_accounts_for_periodic_accounting():
			account_bal, stock_bal, _warehouse_list = get_stock_and_account_balance(
				account, self.posting_date, self.company
			)
			difference_value = flt(stock_bal - account_bal, self.precision("difference"))
			if difference_value == 0:
				frappe.msgprint(
					_("No difference found for stock account {0}").format(frappe.bold(account)),
					alert=True,
				)
				continue

			self._append_periodic_difference_rows(account, difference_value)

	def _append_periodic_difference_rows(self, account: str, difference_value: float) -> None:
		"""Append the stock account row and its offsetting difference-account row."""
		self.append(
			"accounts",
			{
				"account": account,
				"debit_in_account_currency": difference_value if difference_value > 0 else 0,
				"credit_in_account_currency": abs(difference_value) if difference_value < 0 else 0,
			},
		)
		self.append(
			"accounts",
			{
				"account": self.periodic_entry_difference_account,
				"credit_in_account_currency": difference_value if difference_value > 0 else 0,
				"debit_in_account_currency": abs(difference_value) if difference_value < 0 else 0,
			},
		)

	def validate_company_for_periodic_accounting(self):
		if erpnext.is_perpetual_inventory_enabled(self.company):
			frappe.throw(
				_(
					"Periodic Accounting Entry is not allowed for company {0} with perpetual inventory enabled"
				).format(self.company)
			)

		if not self.periodic_entry_difference_account:
			frappe.throw(_("Please select Periodic Accounting Entry Difference Account"))

	def get_stock_accounts_for_periodic_accounting(self):
		if self.voucher_type != "Periodic Accounting Entry":
			return []

		if self.for_all_stock_asset_accounts:
			return frappe.get_all(
				"Account",
				filters={
					"company": self.company,
					"account_type": "Stock",
					"root_type": "Asset",
					"is_group": 0,
				},
				pluck="name",
			)

		if not self.stock_asset_account:
			frappe.throw(_("Please select Stock Asset Account"))

		return [self.stock_asset_account]

	def on_update_after_submit(self):
		# Flag will be set on Reconciliation
		# Reconciliation tool will anyways repost ledger entries. So, no need to check and do implicit repost.
		if self.flags.get("ignore_reposting_on_reconciliation"):
			return

		self.needs_repost = self.check_if_fields_updated(fields_to_check=[], child_tables={"accounts": []})
		if self.needs_repost:
			self.validate_for_repost()
			self.repost_accounting_entries()

	def on_cancel(self):
		"""Reverse GL entries and unlink asset, inter-company and advance references on cancel."""
		# Cancel tax withholding entries

		from erpnext.accounts.doctype.journal_entry.services.asset_service import AssetService

		# References for this Journal are removed on the `on_cancel` event in accounts_controller
		super().on_cancel()

		from_doc_events = getattr(self, "ignore_linked_doctypes", ())
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
			"Advance Payment Ledger Entry",
			"Tax Withholding Entry",
		)

		if from_doc_events and from_doc_events != self.ignore_linked_doctypes:
			self.ignore_linked_doctypes = self.ignore_linked_doctypes + from_doc_events

		self.make_gl_entries(1)
		JournalTaxWithholding(self).on_cancel()
		self.unlink_advance_entry_reference()
		AssetService(self).unlink_asset_reference()
		self.unlink_inter_company_jv()
		AssetService(self).unlink_asset_adjustment_entry()
		self.update_invoice_discounting()

	def get_title(self):
		return self.pay_to_recd_from or self.accounts[0].account

	def validate_inter_company_accounts(self):
		if self.voucher_type == "Inter Company Journal Entry" and self.inter_company_journal_entry_reference:
			doc = frappe.db.get_value(
				"Journal Entry",
				self.inter_company_journal_entry_reference,
				["company", "total_debit", "total_credit"],
				as_dict=True,
			)
			account_currency = frappe.get_cached_value("Company", self.company, "default_currency")
			previous_account_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
			if account_currency == previous_account_currency:
				credit_precision = self.precision("total_credit")
				debit_precision = self.precision("total_debit")
				if (flt(self.total_credit, credit_precision) != flt(doc.total_debit, debit_precision)) or (
					flt(self.total_debit, debit_precision) != flt(doc.total_credit, credit_precision)
				):
					frappe.throw(_("Total Credit/ Debit Amount should be same as linked Journal Entry"))

	def validate_stock_accounts(self):
		if (
			not erpnext.is_perpetual_inventory_enabled(self.company)
			or self.voucher_type == "Periodic Accounting Entry"
		):
			# Skip validation for periodic accounting entry and Perpetual Inventory Disabled Company.
			return

		stock_accounts = get_stock_accounts(self.company, accounts=self.accounts)
		for account in stock_accounts:
			account_bal, stock_bal, warehouse_list = get_stock_and_account_balance(
				account, self.posting_date, self.company
			)

			if account_bal == stock_bal:
				frappe.throw(
					_("Account: {0} can only be updated via Stock Transactions").format(account),
					StockAccountInvalidTransaction,
				)

	def update_inter_company_jv(self):
		if self.voucher_type == "Inter Company Journal Entry" and self.inter_company_journal_entry_reference:
			frappe.db.set_value(
				"Journal Entry",
				self.inter_company_journal_entry_reference,
				"inter_company_journal_entry_reference",
				self.name,
			)

	def update_invoice_discounting(self) -> None:
		"""Advance each linked Invoice Discounting to its next status on submit/cancel."""
		discounting_names = {
			row.reference_name for row in self.accounts if row.reference_type == "Invoice Discounting"
		}
		for name in discounting_names:
			inv_disc = frappe.get_doc("Invoice Discounting", name)
			if status := self._get_next_invoice_discounting_status(inv_disc):
				inv_disc.set_status(status=status)

	def _get_next_invoice_discounting_status(self, inv_disc) -> str | None:
		"""Validate the current status and return the next one from the loan account row."""
		for row in self.accounts:
			if row.account != inv_disc.short_term_loan or row.reference_name != inv_disc.name:
				continue

			submitting = self.docstatus == 1
			if row.credit > 0:
				expected, next_status = (
					("Sanctioned", "Disbursed") if submitting else ("Disbursed", "Sanctioned")
				)
			elif row.debit > 0:
				expected, next_status = ("Disbursed", "Settled") if submitting else ("Settled", "Disbursed")
			else:
				return None

			self._validate_invoice_discounting_status(inv_disc, expected, row.idx)
			return next_status
		return None

	def _validate_invoice_discounting_status(self, inv_disc, expected_status: str, row_idx: int) -> None:
		"""Throw unless the Invoice Discounting is in the status expected for this transition."""
		if inv_disc.status != expected_status:
			frappe.throw(
				_("Row #{0}: Status must be {1} for Invoice Discounting {2}").format(
					row_idx, expected_status, get_link_to_form("Invoice Discounting", inv_disc.name)
				)
			)

	def unlink_advance_entry_reference(self):
		for d in self.get("accounts"):
			if d.is_advance == "Yes" and d.reference_type in ("Sales Invoice", "Purchase Invoice"):
				doc = frappe.get_doc(d.reference_type, d.reference_name)
				doc.delink_advance_entries(self.name)
				d.reference_type = ""
				d.reference_name = ""
				d.db_update()

	def unlink_inter_company_jv(self):
		if self.voucher_type == "Inter Company Journal Entry" and self.inter_company_journal_entry_reference:
			frappe.db.set_value(
				"Journal Entry",
				self.inter_company_journal_entry_reference,
				"inter_company_journal_entry_reference",
				"",
			)
			frappe.db.set_value("Journal Entry", self.name, "inter_company_journal_entry_reference", "")

	def validate_party(self):
		for d in self.get("accounts"):
			account_type = frappe.get_cached_value("Account", d.account, "account_type")

			if account_type in ["Receivable", "Payable"]:
				if (
					not (d.party_type and d.party) and not self.party_not_required
				):  # skipping validation if party_not_required is passed via payroll entry
					frappe.throw(
						_(
							"Row {0}: Party Type and Party is required for Receivable / Payable account {1}"
						).format(d.idx, d.account)
					)
				elif (
					d.party_type
					and frappe.db.get_value("Party Type", d.party_type, "account_type") != account_type
					and d.party_type
					!= "Employee"  # making an excpetion for employee since they can be both payable and receivable
				):
					frappe.throw(
						_("Row {0}: Account {1} and Party Type {2} have different account types").format(
							d.idx, d.account, d.party_type
						)
					)

	def check_credit_limit(self):
		customers = list(
			set(
				d.party
				for d in self.get("accounts")
				if d.party_type == "Customer" and d.party and flt(d.debit) > 0
			)
		)
		if customers:
			from erpnext.selling.doctype.customer.customer import check_credit_limit

			customer_details = frappe._dict(
				frappe.db.get_all(
					"Customer Credit Limit",
					filters={
						"parent": ["in", customers],
						"parenttype": ["=", "Customer"],
						"company": ["=", self.company],
					},
					fields=["parent", "bypass_credit_limit_check"],
					as_list=True,
				)
			)

			for customer in customers:
				ignore_outstanding_sales_order = bool(customer_details.get(customer))
				check_credit_limit(customer, self.company, ignore_outstanding_sales_order)

	def validate_cheque_info(self):
		if self.voucher_type in ["Bank Entry"]:
			if not self.cheque_no or not self.cheque_date:
				msgprint(
					_("Reference No & Reference Date is required for {0}").format(self.voucher_type),
					raise_exception=1,
				)

		if self.cheque_date and not self.cheque_no:
			msgprint(_("Reference No is mandatory if you entered Reference Date"), raise_exception=1)

	def validate_entries_for_advance(self):
		for d in self.get("accounts"):
			if d.reference_type not in ("Sales Invoice", "Purchase Invoice", "Journal Entry"):
				if (d.party_type == "Customer" and flt(d.credit) > 0) or (
					d.party_type == "Supplier" and flt(d.debit) > 0
				):
					if d.is_advance == "No":
						msgprint(
							_(
								"Row {0}: Please check 'Is Advance' against Account {1} if this is an advance entry."
							).format(d.idx, d.account),
							alert=True,
						)
					elif d.reference_type in ("Sales Order", "Purchase Order") and d.is_advance != "Yes":
						frappe.throw(
							_(
								"Row {0}: Payment against Sales/Purchase Order should always be marked as advance"
							).format(d.idx)
						)

				if d.is_advance == "Yes":
					if d.party_type == "Customer" and flt(d.debit) > 0:
						frappe.throw(_("Row {0}: Advance against Customer must be credit").format(d.idx))
					elif d.party_type == "Supplier" and flt(d.credit) > 0:
						frappe.throw(_("Row {0}: Advance against Supplier must be debit").format(d.idx))

	def system_generated_gain_loss(self):
		return (
			self.voucher_type == "Exchange Gain Or Loss" and self.multi_currency and self.is_system_generated
		)

	def validate_against_jv(self) -> None:
		"""Validate every account row that references another Journal Entry."""
		for row in self.get("accounts"):
			if row.reference_type == "Journal Entry":
				self._validate_jv_reference(row)

	def _validate_jv_reference(self, row) -> None:
		"""Validate a single 'Against Journal Entry' row: direction, no self-reference,
		and the presence of an unmatched entry on the referenced Journal Entry."""
		self._validate_jv_reference_direction(row)

		if row.reference_name == self.name:
			frappe.throw(_("You can not enter current voucher in 'Against Journal Entry' column"))

		against_entries = self._get_against_jv_entries(row)
		if not against_entries:
			if self.voucher_type != "Exchange Gain Or Loss":
				frappe.throw(
					_(
						"Journal Entry {0} does not have account {1} or already matched against other voucher"
					).format(row.reference_name, row.account)
				)
			return

		dr_or_cr = "debit" if flt(row.credit) > 0 else "credit"
		has_unmatched_entry = any(flt(entry[dr_or_cr]) > 0 for entry in against_entries)
		if not has_unmatched_entry and not self.system_generated_gain_loss():
			frappe.throw(
				_("Against Journal Entry {0} does not have any unmatched {1} entry").format(
					row.reference_name, dr_or_cr
				)
			)

	def _validate_jv_reference_direction(self, row) -> None:
		"""An asset account can reference a JE only when credited, a liability only when debited."""
		if self.system_generated_gain_loss():
			return

		account_root_type = frappe.get_cached_value("Account", row.account, "root_type")
		if account_root_type == "Asset" and flt(row.debit) > 0:
			frappe.throw(
				_(
					"Row #{0}: For {1}, you can select reference document only if account gets credited"
				).format(row.idx, row.account)
			)
		if account_root_type == "Liability" and flt(row.credit) > 0:
			frappe.throw(
				_("Row #{0}: For {1}, you can select reference document only if account gets debited").format(
					row.idx, row.account
				)
			)

	def _get_against_jv_entries(self, row) -> list[dict]:
		"""Submitted Journal Entry Account rows on the referenced JE for the same account
		that are not themselves linked to an order."""
		jea = frappe.qb.DocType("Journal Entry Account")
		return (
			frappe.qb.from_(jea)
			.select(jea.star)
			.where(
				(jea.account == row.account)
				& (jea.docstatus == 1)
				& (jea.parent == row.reference_name)
				& (
					jea.reference_type.isnull()
					| jea.reference_type.isin(["", "Sales Order", "Purchase Order"])
				)
			)
			.run(as_dict=True)
		)

	def set_against_account(self):
		accounts_debited, accounts_credited = [], []
		if self.voucher_type in ("Deferred Revenue", "Deferred Expense"):
			for d in self.get("accounts"):
				if d.reference_type == "Sales Invoice":
					field = "customer"
				else:
					field = "supplier"

				d.against_account = frappe.db.get_value(d.reference_type, d.reference_name, field)
		else:
			for d in self.get("accounts"):
				if flt(d.debit) > 0:
					accounts_debited.append(d.party or d.account)
				if flt(d.credit) > 0:
					accounts_credited.append(d.party or d.account)

			for d in self.get("accounts"):
				if flt(d.debit) > 0:
					d.against_account = ", ".join(list(set(accounts_credited)))
				if flt(d.credit) > 0:
					d.against_account = ", ".join(list(set(accounts_debited)))

	def validate_debit_credit_amount(self):
		if not (self.voucher_type == "Exchange Gain Or Loss" and self.multi_currency):
			for d in self.get("accounts"):
				if not flt(d.debit) and not flt(d.credit):
					frappe.throw(_("Row {0}: Both Debit and Credit values cannot be zero").format(d.idx))

	def validate_total_debit_and_credit(self):
		if not (self.voucher_type == "Exchange Gain Or Loss" and self.multi_currency):
			if self.difference:
				frappe.throw(
					_("Total Debit must be equal to Total Credit. The difference is {0}").format(
						self.difference
					)
				)

	def set_total_debit_credit(self):
		self.total_debit, self.total_credit, self.difference = 0, 0, 0
		for d in self.get("accounts"):
			if d.debit and d.credit:
				frappe.throw(_("You cannot credit and debit same account at the same time"))

			self.total_debit = flt(self.total_debit) + flt(d.debit, d.precision("debit"))
			self.total_credit = flt(self.total_credit) + flt(d.credit, d.precision("credit"))

		self.difference = flt(self.total_debit, self.precision("total_debit")) - flt(
			self.total_credit, self.precision("total_credit")
		)

	def validate_multi_currency(self):
		alternate_currency = []
		for d in self.get("accounts"):
			account = frappe.get_cached_value(
				"Account", d.account, ["account_currency", "account_type"], as_dict=1
			)
			if account:
				d.account_currency = account.account_currency
				d.account_type = account.account_type

			if not d.account_currency:
				d.account_currency = self.company_currency

			if d.account_currency != self.company_currency and d.account_currency not in alternate_currency:
				alternate_currency.append(d.account_currency)

		if alternate_currency:
			if not self.multi_currency:
				frappe.throw(_("Please check Multi Currency option to allow accounts with other currency"))

		self.set_exchange_rate()

	def set_amounts_in_company_currency(self):
		if not (self.voucher_type == "Exchange Gain Or Loss" and self.multi_currency):
			for d in self.get("accounts"):
				d.debit_in_account_currency = flt(
					d.debit_in_account_currency, d.precision("debit_in_account_currency")
				)
				d.credit_in_account_currency = flt(
					d.credit_in_account_currency, d.precision("credit_in_account_currency")
				)

				d.debit = flt(d.debit_in_account_currency * flt(d.exchange_rate), d.precision("debit"))
				d.credit = flt(d.credit_in_account_currency * flt(d.exchange_rate), d.precision("credit"))

	def set_exchange_rate(self) -> None:
		"""Resolve a mandatory exchange rate for every account row."""
		for row in self.get("accounts"):
			self._set_row_exchange_rate(row)
			if not row.exchange_rate:
				frappe.throw(_("Row {0}: Exchange Rate is mandatory").format(row.idx))

	def _set_row_exchange_rate(self, row) -> None:
		"""Set a row's exchange rate: 1 for company currency, otherwise fetched when stale."""
		if row.account_currency == self.company_currency:
			row.exchange_rate = 1
			return

		needs_refresh = (
			not row.exchange_rate
			or row.exchange_rate == 1
			or (
				row.reference_type in ("Sales Invoice", "Purchase Invoice")
				and row.reference_name
				and self.posting_date
			)
		)
		if not needs_refresh or self.flags.get("ignore_exchange_rate"):
			return

		# Includes the posting date for which to retrieve the exchange rate
		row.exchange_rate = get_exchange_rate(
			self.posting_date,
			row.account,
			row.account_currency,
			self.company,
			row.reference_type,
			row.reference_name,
			row.debit,
			row.credit,
			row.exchange_rate,
		)

	def create_remarks(self) -> None:
		"""Build the auto remark from the cheque reference and each account row's linked
		document, unless remark creation is skipped or a custom remark is set."""
		if self.flags.skip_remarks_creation or self.get("custom_remark"):
			return

		remarks = []
		if cheque_remark := self._get_cheque_remark():
			remarks.append(cheque_remark)

		for row in self.get("accounts"):
			if reference_remark := self._get_reference_remark(row):
				remarks.append(reference_remark)

		if remarks:
			self.remark = "\n".join(remarks)  # User Remarks is not mandatory

	def _get_cheque_remark(self) -> str | None:
		"""Remark line for the cheque reference; raises if the cheque date is missing."""
		if not self.cheque_no:
			return None
		if not self.cheque_date:
			msgprint(_("Please enter Reference date"), raise_exception=frappe.MandatoryError)
		return _("Reference #{0} dated {1}").format(self.cheque_no, formatdate(self.cheque_date))

	def _get_reference_remark(self, row) -> str | None:
		"""Remark line for a single account row's linked Invoice/Order, or None."""
		if row.reference_type == "Sales Invoice" and row.credit:
			return _("{0} against Sales Invoice {1}").format(
				fmt_money(flt(row.credit), currency=self.company_currency), row.reference_name
			)
		if row.reference_type == "Sales Order" and row.credit:
			return _("{0} against Sales Order {1}").format(
				fmt_money(flt(row.credit), currency=self.company_currency), row.reference_name
			)
		if row.reference_type == "Purchase Invoice" and row.debit:
			return self._get_bill_remark(row)
		if row.reference_type == "Purchase Order" and row.debit:
			return _("{0} against Purchase Order {1}").format(
				fmt_money(flt(row.credit), currency=self.company_currency), row.reference_name
			)
		return None

	def _get_bill_remark(self, row) -> str | None:
		"""Remark line referencing the supplier bill number/date of a Purchase Invoice row."""
		bill_no, bill_date = frappe.db.get_value(
			"Purchase Invoice", row.reference_name, ["bill_no", "bill_date"]
		) or (None, None)
		if not bill_no or bill_no.lower().strip() in ["na", "not applicable", "none"]:
			return None
		return _("{0} against Bill {1} dated {2}").format(
			fmt_money(flt(row.debit), currency=self.company_currency),
			bill_no,
			bill_date and formatdate(bill_date.strftime("%Y-%m-%d")),
		)

	def set_print_format_fields(self) -> None:
		"""Populate pay_to_recd_from and the total amount/currency shown on the print format."""
		amounts = self._get_party_and_bank_amounts()

		total_amount, currency = 0.0, None
		if amounts.party_type and amounts.pay_to_recd_from:
			self.pay_to_recd_from = frappe.db.get_value(
				amounts.party_type,
				amounts.pay_to_recd_from,
				"customer_name" if amounts.party_type == "Customer" else "supplier_name",
			)
			if amounts.bank_amount:
				total_amount, currency = amounts.bank_amount, amounts.bank_account_currency
			else:
				total_amount, currency = amounts.party_amount, amounts.party_account_currency

		self.set_total_amount(total_amount, currency)

	def _get_party_and_bank_amounts(self) -> frappe._dict:
		"""Sum the party and bank/cash amounts, with their currencies, across the account rows."""
		totals = frappe._dict(
			bank_amount=0.0,
			party_amount=0.0,
			bank_account_currency=None,
			party_account_currency=None,
			pay_to_recd_from=None,
			party_type=None,
		)
		for row in self.get("accounts"):
			amount = flt(row.debit_in_account_currency) or flt(row.credit_in_account_currency)
			if row.party_type in ["Customer", "Supplier"] and row.party:
				totals.party_type = row.party_type
				totals.pay_to_recd_from = totals.pay_to_recd_from or row.party
				if totals.pay_to_recd_from == row.party:
					totals.party_amount += amount
					totals.party_account_currency = row.account_currency
			elif frappe.get_cached_value("Account", row.account, "account_type") in ["Bank", "Cash"]:
				totals.bank_amount += amount
				totals.bank_account_currency = row.account_currency
		return totals

	def set_total_amount(self, amt: float, currency: str) -> None:
		self.total_amount = amt
		self.total_amount_currency = currency
		from frappe.utils import money_in_words

		self.total_amount_in_words = money_in_words(amt, currency)

	def build_gl_map(self):
		from erpnext.accounts.doctype.journal_entry.services.gl_composer import JournalEntryGLComposer

		return JournalEntryGLComposer(self).compose()

	def make_gl_entries(self, cancel: int = 0, adv_adj: int = 0) -> None:
		from erpnext.accounts.general_ledger import make_gl_entries

		merge_entries = frappe.get_single_value("Accounts Settings", "merge_similar_account_heads")

		gl_map = self.build_gl_map()
		if self.voucher_type in ("Deferred Revenue", "Deferred Expense"):
			update_outstanding = "No"
		else:
			update_outstanding = "Yes"

		if gl_map:
			make_gl_entries(
				gl_map,
				cancel=cancel,
				adv_adj=adv_adj,
				merge_entries=merge_entries,
				update_outstanding=update_outstanding,
			)
			frappe.flags.party_not_required = False
			if cancel:
				cancel_exchange_gain_loss_journal(frappe._dict(doctype=self.doctype, name=self.name))

	@frappe.whitelist()
	def get_balance(self, difference_account: str | None = None) -> None:
		"""Balance the entry by placing any difference on a blank (or newly added) row."""
		if not self.get("accounts"):
			msgprint(_("'Entries' cannot be empty"), raise_exception=True)
			return

		self.total_debit, self.total_credit = 0, 0
		diff = flt(self.difference, self.precision("difference"))
		if diff:
			self._apply_difference_to_blank_row(diff, difference_account)

		self.set_total_debit_credit()
		self.validate_total_debit_and_credit()

	def _apply_difference_to_blank_row(self, diff: float, difference_account: str | None) -> None:
		"""Set the balancing difference on the last amountless row, adding one if none exists."""
		blank_row = None
		for row in self.get("accounts"):
			if not row.credit_in_account_currency and not row.debit_in_account_currency:
				blank_row = row

		if not blank_row:
			blank_row = self.append(
				"accounts",
				{
					"account": difference_account,
					"cost_center": erpnext.get_default_cost_center(self.company),
				},
			)

		blank_row.exchange_rate = 1
		if diff > 0:
			blank_row.credit_in_account_currency = diff
			blank_row.credit = diff
		elif diff < 0:
			blank_row.debit_in_account_currency = abs(diff)
			blank_row.debit = abs(diff)

	@frappe.whitelist()
	def get_outstanding_invoices(self) -> None:
		"""Populate the entry with a write-off row per outstanding invoice plus a balancing row."""
		self.set("accounts", [])
		total = 0
		for invoice in self.get_values():
			total += flt(invoice.outstanding_amount, self.precision("credit", "accounts"))
			self._append_outstanding_invoice_row(invoice)

		balancing_row = self.append("accounts", {})
		if self.write_off_based_on == "Accounts Receivable":
			balancing_row.debit_in_account_currency = total
		elif self.write_off_based_on == "Accounts Payable":
			balancing_row.credit_in_account_currency = total

		self.validate_total_debit_and_credit()

	def _append_outstanding_invoice_row(self, invoice) -> None:
		"""Append a party row for a single outstanding invoice per the write-off basis."""
		row = self.append("accounts", {})
		row.account = invoice.account
		row.party = invoice.party

		if self.write_off_based_on == "Accounts Receivable":
			row.party_type = "Customer"
			row.credit_in_account_currency = flt(
				invoice.outstanding_amount, self.precision("credit", "accounts")
			)
			row.reference_type = "Sales Invoice"
			row.reference_name = cstr(invoice.name)
		elif self.write_off_based_on == "Accounts Payable":
			row.party_type = "Supplier"
			row.debit_in_account_currency = flt(
				invoice.outstanding_amount, self.precision("debit", "accounts")
			)
			row.reference_type = "Purchase Invoice"
			row.reference_name = cstr(invoice.name)

	def get_values(self):
		if self.write_off_based_on == "Accounts Receivable":
			doctype, account_field, party_field = "Sales Invoice", "debit_to", "customer"
		elif self.write_off_based_on == "Accounts Payable":
			doctype, account_field, party_field = "Purchase Invoice", "credit_to", "supplier"
		else:
			return

		invoice = frappe.qb.DocType(doctype)
		query = (
			frappe.qb.from_(invoice)
			.select(
				invoice.name,
				invoice[account_field].as_("account"),
				invoice[party_field].as_("party"),
				invoice.outstanding_amount,
			)
			.where(
				(invoice.docstatus == 1)
				& (invoice.company == self.company)
				& (invoice.outstanding_amount > 0)
			)
		)
		if flt(self.write_off_amount) > 0:
			query = query.where(invoice.outstanding_amount <= flt(self.write_off_amount))

		return query.run(as_dict=True)

	def validate_credit_debit_note(self):
		if self.stock_entry:
			if frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") != 1:
				frappe.throw(_("Stock Entry {0} is not submitted").format(self.stock_entry))

			if frappe.db.exists(
				{"doctype": "Journal Entry", "stock_entry": self.stock_entry, "docstatus": 1}
			):
				frappe.msgprint(
					_("Warning: Another {0} # {1} exists against stock entry {2}").format(
						self.voucher_type, self.name, self.stock_entry
					)
				)

	def validate_empty_accounts_table(self):
		if not self.get("accounts"):
			frappe.throw(_("Accounts table cannot be blank."))


@frappe.whitelist()
def get_default_bank_cash_account(
	company: str,
	account_type: str | None = None,
	mode_of_payment: str | None = None,
	account: str | None = None,
	*,
	fetch_balance: bool = True,
) -> dict:
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

	if mode_of_payment:
		account = get_bank_cash_account(mode_of_payment, company).get("account")

	if not account:
		"""
		Set the default account first. If the user hasn't set any default account then, he doesn't
		want us to set any random account. In this case set the account only if there is single
		account (of that type), otherwise return empty dict.
		"""
		if account_type == "Bank":
			account = frappe.get_cached_value("Company", company, "default_bank_account")
			if not account:
				account_list = frappe.get_all(
					"Account", filters={"company": company, "account_type": "Bank", "is_group": 0}
				)
				if len(account_list) == 1:
					account = account_list[0].name

		elif account_type == "Cash":
			account = frappe.get_cached_value("Company", company, "default_cash_account")
			if not account:
				account_list = frappe.get_all(
					"Account", filters={"company": company, "account_type": "Cash", "is_group": 0}
				)
				if len(account_list) == 1:
					account = account_list[0].name

	if account:
		account_details = frappe.get_cached_value(
			"Account", account, ["account_currency", "account_type"], as_dict=1
		)
		result = {
			"account": account,
			"account_currency": account_details.account_currency,
			"account_type": account_details.account_type,
		}
		if fetch_balance:
			result["balance"] = get_balance_on(account)
		return frappe._dict(result)
	else:
		return frappe._dict()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_against_jv(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict,
) -> list:
	"""Link-field search for submitted Journal Entries having an unreferenced row on an account."""
	if not frappe.db.has_column("Journal Entry", searchfield):
		return []

	JournalEntry = frappe.qb.DocType("Journal Entry")
	JournalEntryAccount = frappe.qb.DocType("Journal Entry Account")

	query = (
		frappe.qb.from_(JournalEntry)
		.join(JournalEntryAccount)
		.on(JournalEntryAccount.parent == JournalEntry.name)
		.select(JournalEntry.name, JournalEntry.posting_date, JournalEntry.remark)
		.where(JournalEntryAccount.account == filters.get("account"))
		.where(JournalEntryAccount.reference_type.isnull() | (JournalEntryAccount.reference_type == ""))
		.where(JournalEntry.docstatus == 1)
		.where(JournalEntry[searchfield].like(f"%{txt}%"))
		.orderby(JournalEntry.name, order=frappe.qb.desc)
		.limit(page_len)
		.offset(start)
	)

	party = filters.get("party")
	if party:
		query = query.where(JournalEntryAccount.party == party)
	else:
		query = query.where(JournalEntryAccount.party.isnull() | (JournalEntryAccount.party == ""))

	return query.run()


@frappe.whitelist()
def get_outstanding(
	doctype: str | None = None,
	docname: str | None = None,
	company: str | None = None,
	account: str | None = None,
	party: str | None = None,
	account_currency: str | None = None,
	**kwargs,
) -> dict | None:
	"""Return the outstanding amount and side to set when referencing a JV / Invoice.

	The named parameters are the supported interface. The legacy `args` payload dict
	(captured via kwargs) is still accepted for backward compatibility with callers,
	including custom apps, and is unpacked into the named parameters below.
	"""
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	if legacy_payload := kwargs.get("args"):
		if isinstance(legacy_payload, str):
			legacy_payload = json.loads(legacy_payload)
		doctype = legacy_payload.get("doctype")
		docname = legacy_payload.get("docname")
		company = legacy_payload.get("company")
		account = legacy_payload.get("account")
		party = legacy_payload.get("party")
		account_currency = legacy_payload.get("account_currency")

	if doctype == "Journal Entry":
		return _get_journal_entry_outstanding(docname, account, party)

	if doctype in ("Sales Invoice", "Purchase Invoice"):
		return _get_invoice_outstanding(doctype, docname, company, account_currency)


def _get_journal_entry_outstanding(docname: str, account: str | None, party: str | None) -> dict:
	"""Unreferenced debit-minus-credit balance for an account on a Journal Entry."""
	jea = frappe.qb.DocType("Journal Entry Account")
	query = (
		frappe.qb.from_(jea)
		.select(Sum(jea.debit_in_account_currency) - Sum(jea.credit_in_account_currency))
		.where(
			(jea.parent == docname)
			& (jea.account == account)
			& (jea.reference_type.isnull() | (jea.reference_type == ""))
		)
	)
	if party:
		query = query.where(jea.party == party)

	result = query.run()
	balance = flt(result[0][0]) if result else 0
	amount_field = "credit_in_account_currency" if balance > 0 else "debit_in_account_currency"
	return {amount_field: abs(balance)}


def _get_invoice_outstanding(doctype: str, docname: str, company: str, account_currency: str | None) -> dict:
	"""Outstanding amount, side, party and exchange rate for a Sales/Purchase Invoice."""
	party_type = "Customer" if doctype == "Sales Invoice" else "Supplier"
	invoice = frappe.db.get_value(
		doctype,
		docname,
		["outstanding_amount", "conversion_rate", scrub(party_type), "due_date"],
		as_dict=1,
	)

	company_currency = erpnext.get_company_currency(company)
	exchange_rate = invoice.conversion_rate if account_currency != company_currency else 1

	outstanding_is_positive = flt(invoice.outstanding_amount) > 0
	if doctype == "Sales Invoice":
		amount_field = (
			"credit_in_account_currency" if outstanding_is_positive else "debit_in_account_currency"
		)
	else:
		amount_field = (
			"debit_in_account_currency" if outstanding_is_positive else "credit_in_account_currency"
		)

	return {
		amount_field: abs(flt(invoice.outstanding_amount)),
		"exchange_rate": exchange_rate,
		"party_type": party_type,
		"party": invoice.get(scrub(party_type)),
		"reference_due_date": invoice.get("due_date"),
	}


@frappe.whitelist()
def get_party_account_and_currency(company: str, party_type: str, party: str) -> dict:
	"""Return the receivable/payable account for a party and its account currency."""
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	account = get_party_account(party_type, party, company)

	return {
		"account": account,
		"account_currency": frappe.get_cached_value("Account", account, "account_currency"),
	}


@frappe.whitelist()
def get_account_details_and_party_type(
	account: str,
	date: str,
	company: str,
	debit: float | str | None = None,
	credit: float | str | None = None,
	exchange_rate: float | str | None = None,
) -> dict:
	"""Returns dict of account details and party type to be set in Journal Entry on selection of account."""
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	company_currency = erpnext.get_company_currency(company)
	account_details = frappe.get_cached_value(
		"Account", account, ["account_type", "account_currency"], as_dict=1
	)

	if not account_details:
		return

	if account_details.account_type == "Receivable":
		party_type = "Customer"
	elif account_details.account_type == "Payable":
		party_type = "Supplier"
	else:
		party_type = ""

	grid_values = {
		"party_type": party_type,
		"account_type": account_details.account_type,
		"account_currency": account_details.account_currency or company_currency,
		"bank_account": (
			frappe.db.get_value("Bank Account", {"account": account, "company": company}) or None
		),
		# The date used to retreive the exchange rate here is the date passed in
		# as an argument to this function. It is assumed to be the date on which the balance is sought
		"exchange_rate": get_exchange_rate(
			date,
			account,
			account_details.account_currency,
			company,
			debit=debit,
			credit=credit,
			exchange_rate=exchange_rate,
		),
	}

	# un-set party if not party type
	if not party_type:
		grid_values["party"] = ""

	return grid_values


@frappe.whitelist()
def get_exchange_rate(
	posting_date: str | date,
	account: str | None = None,
	account_currency: str | None = None,
	company: str | None = None,
	reference_type: str | None = None,
	reference_name: str | None = None,
	debit: float | str | None = None,
	credit: float | str | None = None,
	exchange_rate: str | float | None = None,
) -> float:
	"""Resolve the exchange rate for an account row, by reference, balance or settings."""
	# Ensure exchange_rate is always numeric to avoid calculation errors
	if isinstance(exchange_rate, str):
		exchange_rate = flt(exchange_rate) or 1

	account_details = frappe.get_cached_value(
		"Account", account, ["account_type", "root_type", "account_currency", "company"], as_dict=1
	)

	if not account_details:
		frappe.throw(_("Please select correct account"))

	if not company:
		company = account_details.company

	if not account_currency:
		account_currency = account_details.account_currency

	company_currency = erpnext.get_company_currency(company)

	if account_currency != company_currency:
		if reference_type in ("Sales Invoice", "Purchase Invoice") and reference_name:
			exchange_rate = frappe.db.get_value(reference_type, reference_name, "conversion_rate")

		# The date used to retreive the exchange rate here is the date passed
		# in as an argument to this function.
		elif (not flt(exchange_rate) or flt(exchange_rate) == 1) and account_currency and posting_date:
			exchange_rate = _get_exchange_rate(account_currency, company_currency, posting_date)
	else:
		exchange_rate = 1

	# don't return None or 0 as it is multipled with a value and that value could be lost
	return exchange_rate or 1
