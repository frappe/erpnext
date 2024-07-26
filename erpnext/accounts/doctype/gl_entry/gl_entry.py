# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.model.naming import set_name_from_naming_options
from frappe.utils import flt, fmt_money

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.accounts.party import validate_party_frozen_disabled, validate_party_gle_currency
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from erpnext.exceptions import InvalidAccountCurrency

exclude_from_linked_with = True


class GLEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		account_currency: DF.Link | None
		against: DF.Text | None
		against_voucher: DF.DynamicLink | None
		against_voucher_type: DF.Link | None
		company: DF.Link | None
		cost_center: DF.Link | None
		credit: DF.Currency
		credit_in_account_currency: DF.Currency
		credit_in_transaction_currency: DF.Currency
		debit: DF.Currency
		debit_in_account_currency: DF.Currency
		debit_in_transaction_currency: DF.Currency
		due_date: DF.Date | None
		finance_book: DF.Link | None
		fiscal_year: DF.Link | None
		is_advance: DF.Literal["No", "Yes"]
		is_cancelled: DF.Check
		is_opening: DF.Literal["No", "Yes"]
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		posting_date: DF.Date | None
		project: DF.Link | None
		remarks: DF.Text | None
		to_rename: DF.Check
		transaction_currency: DF.Link | None
		transaction_date: DF.Date | None
		transaction_exchange_rate: DF.Float
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink | None
		voucher_subtype: DF.SmallText | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	def autoname(self):
		"""
		Temporarily name doc for fast insertion
		name will be changed using autoname options (in a scheduled job)
		"""
		self.name = frappe.generate_hash(txt="", length=10)
		if self.meta.autoname == "hash":
			self.to_rename = 0

	def validate(self):
		self.flags.ignore_submit_comment = True
		self.validate_and_set_fiscal_year()
		self.pl_must_have_cost_center()

		if not self.flags.from_repost and self.voucher_type != "Period Closing Voucher":
			self.check_mandatory()
			self.validate_cost_center()
			self.check_pl_account()
			self.validate_party()
			self.validate_currency()

	def on_update(self):
		adv_adj = self.flags.adv_adj
		if not self.flags.from_repost and self.voucher_type != "Period Closing Voucher":
			self.validate_account_details(adv_adj)
			self.validate_dimensions_for_pl_and_bs()
			validate_balance_type(self.account, adv_adj)
			validate_frozen_account(self.account, adv_adj)

			if (
				self.voucher_type == "Journal Entry"
				and frappe.get_cached_value("Journal Entry", self.voucher_no, "voucher_type")
				== "Exchange Gain Or Loss"
			):
				return

			if frappe.get_cached_value("Account", self.account, "account_type") not in [
				"Receivable",
				"Payable",
			]:
				# Update outstanding amt on against voucher
				if (
					self.against_voucher_type
					in ["Journal Entry", "Sales Invoice", "Purchase Invoice", "Fees"]
					and self.against_voucher
					and self.flags.update_outstanding == "Yes"
					and not frappe.flags.is_reverse_depr_entry
				):
					update_outstanding_amt(
						self.account,
						self.party_type,
						self.party,
						self.against_voucher_type,
						self.against_voucher,
					)

	def check_mandatory(self):
		mandatory = ["account", "voucher_type", "voucher_no", "company"]
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(_(self.meta.get_label(k))))

		if not (self.party_type and self.party):
			account_type = frappe.get_cached_value("Account", self.account, "account_type")
			if account_type == "Receivable":
				frappe.throw(
					_("{0} {1}: Customer is required against Receivable account {2}").format(
						self.voucher_type, self.voucher_no, self.account
					)
				)
			elif account_type == "Payable":
				frappe.throw(
					_("{0} {1}: Supplier is required against Payable account {2}").format(
						self.voucher_type, self.voucher_no, self.account
					)
				)

		# Zero value transaction is not allowed
		if not (
			flt(self.debit, self.precision("debit"))
			or flt(self.credit, self.precision("credit"))
			or (
				self.voucher_type == "Journal Entry"
				and frappe.get_cached_value("Journal Entry", self.voucher_no, "voucher_type")
				== "Exchange Gain Or Loss"
			)
		):
			frappe.throw(
				_("{0} {1}: Either debit or credit amount is required for {2}").format(
					self.voucher_type, self.voucher_no, self.account
				)
			)

	def pl_must_have_cost_center(self):
		"""Validate that profit and loss type account GL entries have a cost center."""

		if self.cost_center or self.voucher_type == "Period Closing Voucher":
			return

		if frappe.get_cached_value("Account", self.account, "report_type") == "Profit and Loss":
			msg = _("{0} {1}: Cost Center is required for 'Profit and Loss' account {2}.").format(
				self.voucher_type, self.voucher_no, self.account
			)
			msg += " "
			msg += _(
				"Please set the cost center field in {0} or setup a default Cost Center for the Company."
			).format(self.voucher_type)

			frappe.throw(msg, title=_("Missing Cost Center"))

	def validate_dimensions_for_pl_and_bs(self):
		account_type = frappe.get_cached_value("Account", self.account, "report_type")

		for dimension in get_checks_for_pl_and_bs_accounts():
			if (
				account_type == "Profit and Loss"
				and self.company == dimension.company
				and dimension.mandatory_for_pl
				and not dimension.disabled
				and not self.is_cancelled
			):
				if not self.get(dimension.fieldname):
					frappe.throw(
						_(
							"Accounting Dimension <b>{0}</b> is required for 'Profit and Loss' account {1}."
						).format(dimension.label, self.account)
					)

			if (
				account_type == "Balance Sheet"
				and self.company == dimension.company
				and dimension.mandatory_for_bs
				and not dimension.disabled
				and not self.is_cancelled
			):
				if not self.get(dimension.fieldname):
					frappe.throw(
						_(
							"Accounting Dimension <b>{0}</b> is required for 'Balance Sheet' account {1}."
						).format(dimension.label, self.account)
					)

	def check_pl_account(self):
		if (
			self.is_opening == "Yes"
			and frappe.get_cached_value("Account", self.account, "report_type") == "Profit and Loss"
			and not self.is_cancelled
		):
			frappe.throw(
				_("{0} {1}: 'Profit and Loss' type account {2} not allowed in Opening Entry").format(
					self.voucher_type, self.voucher_no, self.account
				)
			)

	def validate_account_details(self, adv_adj):
		"""Account must be ledger, active and not freezed"""

		ret = frappe.db.sql(
			"""select is_group, docstatus, company
			from tabAccount where name=%s""",
			self.account,
			as_dict=1,
		)[0]

		if ret.is_group == 1:
			frappe.throw(
				_(
					"""{0} {1}: Account {2} is a Group Account and group accounts cannot be used in transactions"""
				).format(self.voucher_type, self.voucher_no, self.account)
			)

		if ret.docstatus == 2:
			frappe.throw(
				_("{0} {1}: Account {2} is inactive").format(self.voucher_type, self.voucher_no, self.account)
			)

		if ret.company != self.company:
			frappe.throw(
				_("{0} {1}: Account {2} does not belong to Company {3}").format(
					self.voucher_type, self.voucher_no, self.account, self.company
				)
			)

	def validate_cost_center(self):
		if not self.cost_center:
			return

		is_group, company = frappe.get_cached_value("Cost Center", self.cost_center, ["is_group", "company"])

		if company != self.company:
			frappe.throw(
				_("{0} {1}: Cost Center {2} does not belong to Company {3}").format(
					self.voucher_type, self.voucher_no, self.cost_center, self.company
				)
			)

		if self.voucher_type != "Period Closing Voucher" and is_group:
			frappe.throw(
				_(
					"""{0} {1}: Cost Center {2} is a group cost center and group cost centers cannot be used in transactions"""
				).format(self.voucher_type, self.voucher_no, frappe.bold(self.cost_center))
			)

	def validate_party(self):
		validate_party_frozen_disabled(self.party_type, self.party)

	def validate_currency(self):
		company_currency = erpnext.get_company_currency(self.company)
		account_currency = get_account_currency(self.account)

		if not self.account_currency:
			self.account_currency = account_currency or company_currency

		if account_currency != self.account_currency:
			frappe.throw(
				_("{0} {1}: Accounting Entry for {2} can only be made in currency: {3}").format(
					self.voucher_type, self.voucher_no, self.account, (account_currency or company_currency)
				),
				InvalidAccountCurrency,
			)

		if self.party_type and self.party:
			validate_party_gle_currency(self.party_type, self.party, self.company, self.account_currency)

	def validate_and_set_fiscal_year(self):
		if not self.fiscal_year:
			self.fiscal_year = get_fiscal_year(self.posting_date, company=self.company)[0]

	def on_cancel(self):
		msg = _("Individual GL Entry cannot be cancelled.")
		msg += "<br>" + _("Please cancel related transaction.")
		frappe.throw(msg)


def validate_balance_type(account, adv_adj=False):
	if not adv_adj and account:
		balance_must_be = frappe.get_cached_value("Account", account, "balance_must_be")
		if balance_must_be:
			balance = frappe.db.sql(
				"""select sum(debit) - sum(credit)
				from `tabGL Entry` where account = %s""",
				account,
			)[0][0]

			if (balance_must_be == "Debit" and flt(balance) < 0) or (
				balance_must_be == "Credit" and flt(balance) > 0
			):
				frappe.throw(
					_("Balance for Account {0} must always be {1}").format(account, _(balance_must_be))
				)


def update_outstanding_amt(
	account, party_type, party, against_voucher_type, against_voucher, on_cancel=False
):
	if party_type and party:
		party_condition = " and party_type={} and party={}".format(
			frappe.db.escape(party_type), frappe.db.escape(party)
		)
	else:
		party_condition = ""

	if against_voucher_type == "Sales Invoice":
		party_account = frappe.get_cached_value(against_voucher_type, against_voucher, "debit_to")
		account_condition = f"and account in ({frappe.db.escape(account)}, {frappe.db.escape(party_account)})"
	else:
		account_condition = f" and account = {frappe.db.escape(account)}"

	# get final outstanding amt
	bal = flt(
		frappe.db.sql(
			f"""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s and against_voucher=%s
		and voucher_type != 'Invoice Discounting'
		{party_condition} {account_condition}""",
			(against_voucher_type, against_voucher),
		)[0][0]
		or 0.0
	)

	if against_voucher_type == "Purchase Invoice":
		bal = -bal
	elif against_voucher_type == "Journal Entry":
		against_voucher_amount = flt(
			frappe.db.sql(
				f"""
			select sum(debit_in_account_currency) - sum(credit_in_account_currency)
			from `tabGL Entry` where voucher_type = 'Journal Entry' and voucher_no = %s
			and account = %s and (against_voucher is null or against_voucher='') {party_condition}""",
				(against_voucher, account),
			)[0][0]
		)

		if not against_voucher_amount:
			frappe.throw(
				_("Against Journal Entry {0} is already adjusted against some other voucher").format(
					against_voucher
				)
			)

		bal = against_voucher_amount + bal
		if against_voucher_amount < 0:
			bal = -bal

		# Validation : Outstanding can not be negative for JV
		if bal < 0 and not on_cancel:
			frappe.throw(
				_("Outstanding for {0} cannot be less than zero ({1})").format(
					against_voucher, fmt_money(bal)
				)
			)

	if against_voucher_type in ["Sales Invoice", "Purchase Invoice", "Fees"]:
		ref_doc = frappe.get_doc(against_voucher_type, against_voucher)

		# Didn't use db_set for optimization purpose
		ref_doc.outstanding_amount = bal
		frappe.db.set_value(against_voucher_type, against_voucher, "outstanding_amount", bal)

		ref_doc.set_status(update=True)


def validate_frozen_account(account, adv_adj=None):
	frozen_account = frappe.get_cached_value("Account", account, "freeze_account")
	if frozen_account == "Yes" and not adv_adj:
		frozen_accounts_modifier = frappe.get_cached_value(
			"Accounts Settings", None, "frozen_accounts_modifier"
		)

		if not frozen_accounts_modifier:
			frappe.throw(_("Account {0} is frozen").format(account))
		elif frozen_accounts_modifier not in frappe.get_roles():
			frappe.throw(_("Not authorized to edit frozen Account {0}").format(account))


def update_against_account(voucher_type, voucher_no):
	entries = frappe.db.get_all(
		"GL Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
		fields=["name", "party", "against", "debit", "credit", "account", "company"],
	)

	if not entries:
		return
	company_currency = erpnext.get_company_currency(entries[0].company)
	precision = get_field_precision(frappe.get_meta("GL Entry").get_field("debit"), company_currency)

	accounts_debited, accounts_credited = [], []
	for d in entries:
		if flt(d.debit, precision) > 0:
			accounts_debited.append(d.party or d.account)
		if flt(d.credit, precision) > 0:
			accounts_credited.append(d.party or d.account)

	for d in entries:
		if flt(d.debit, precision) > 0:
			new_against = ", ".join(list(set(accounts_credited)))
		if flt(d.credit, precision) > 0:
			new_against = ", ".join(list(set(accounts_debited)))

		if d.against != new_against:
			frappe.db.set_value("GL Entry", d.name, "against", new_against)


def on_doctype_update():
	frappe.db.add_index("GL Entry", ["against_voucher_type", "against_voucher"])
	frappe.db.add_index("GL Entry", ["voucher_type", "voucher_no"])


def rename_gle_sle_docs():
	for doctype in ["GL Entry", "Stock Ledger Entry"]:
		rename_temporarily_named_docs(doctype)


def rename_temporarily_named_docs(doctype):
	"""Rename temporarily named docs using autoname options"""
	docs_to_rename = frappe.get_all(doctype, {"to_rename": "1"}, order_by="creation", limit=50000)
	for doc in docs_to_rename:
		oldname = doc.name
		set_name_from_naming_options(frappe.get_meta(doctype).autoname, doc)
		newname = doc.name
		frappe.db.sql(
			f"UPDATE `tab{doctype}` SET name = %s, to_rename = 0 where name = %s",
			(newname, oldname),
			auto_commit=True,
		)
