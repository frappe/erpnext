# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, fmt_money, getdate, formatdate
from frappe.model.document import Document
from frappe.model.naming import set_name_from_naming_options
from erpnext.accounts.party import validate_party_gle_currency, validate_party_frozen_disabled
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.utils import get_fiscal_year
from erpnext.exceptions import InvalidAccountCurrency

exclude_from_linked_with = True
class GLEntry(Document):
	def autoname(self):
		"""
		Temporarily name doc for fast insertion
		name will be changed using autoname options (in a scheduled job)
		"""
		self.name = frappe.generate_hash(txt="", length=10)

	def validate(self):
		self.flags.ignore_submit_comment = True
		self.check_mandatory()
		self.validate_and_set_fiscal_year()

		if not self.flags.from_repost:
			self.pl_must_have_cost_center()
			self.check_pl_account()
			self.validate_cost_center()
			self.validate_party()
			self.validate_currency()


	def on_update_with_args(self, adv_adj, update_outstanding = 'Yes', from_repost=False):
		if not from_repost:
			self.validate_account_details(adv_adj)
			check_freezing_date(self.posting_date, adv_adj)

		validate_frozen_account(self.account, adv_adj)
		validate_balance_type(self.account, adv_adj)

		# Update outstanding amt on against voucher
		if self.against_voucher_type in ['Journal Entry', 'Sales Invoice', 'Purchase Invoice', 'Fees'] \
			and self.against_voucher and update_outstanding == 'Yes' and not from_repost:
				update_outstanding_amt(self.account, self.party_type, self.party, self.against_voucher_type,
					self.against_voucher)

	def check_mandatory(self):
		mandatory = ['account','voucher_type','voucher_no','company']
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(_(self.meta.get_label(k))))

		account_type = frappe.db.get_value("Account", self.account, "account_type")
		if not (self.party_type and self.party):
			if account_type == "Receivable":
				frappe.throw(_("{0} {1}: Customer is required against Receivable account {2}")
					.format(self.voucher_type, self.voucher_no, self.account))
			elif account_type == "Payable":
				frappe.throw(_("{0} {1}: Supplier is required against Payable account {2}")
					.format(self.voucher_type, self.voucher_no, self.account))

		# Zero value transaction is not allowed
		if not (flt(self.debit) or flt(self.credit)):
			frappe.throw(_("{0} {1}: Either debit or credit amount is required for {2}")
				.format(self.voucher_type, self.voucher_no, self.account))

	def pl_must_have_cost_center(self):
		if frappe.db.get_value("Account", self.account, "report_type") == "Profit and Loss":
			if not self.cost_center and self.voucher_type != 'Period Closing Voucher':
				frappe.throw(_("{0} {1}: Cost Center is required for 'Profit and Loss' account {2}. Please set up a default Cost Center for the Company.")
					.format(self.voucher_type, self.voucher_no, self.account))
		else:
			from erpnext.accounts.utils import get_allow_cost_center_in_entry_of_bs_account
			if not get_allow_cost_center_in_entry_of_bs_account() and self.cost_center:
				self.cost_center = None
			if self.project:
				self.project = None

	def check_pl_account(self):
		if self.is_opening=='Yes' and \
				frappe.db.get_value("Account", self.account, "report_type")=="Profit and Loss":
			frappe.throw(_("{0} {1}: 'Profit and Loss' type account {2} not allowed in Opening Entry")
				.format(self.voucher_type, self.voucher_no, self.account))

	def validate_account_details(self, adv_adj):
		"""Account must be ledger, active and not freezed"""

		ret = frappe.db.sql("""select is_group, docstatus, company
			from tabAccount where name=%s""", self.account, as_dict=1)[0]

		if ret.is_group==1:
			frappe.throw(_("{0} {1}: Account {2} cannot be a Group")
				.format(self.voucher_type, self.voucher_no, self.account))

		if ret.docstatus==2:
			frappe.throw(_("{0} {1}: Account {2} is inactive")
				.format(self.voucher_type, self.voucher_no, self.account))

		if ret.company != self.company:
			frappe.throw(_("{0} {1}: Account {2} does not belong to Company {3}")
				.format(self.voucher_type, self.voucher_no, self.account, self.company))

	def validate_cost_center(self):
		if not hasattr(self, "cost_center_company"):
			self.cost_center_company = {}

		def _get_cost_center_company():
			if not self.cost_center_company.get(self.cost_center):
				self.cost_center_company[self.cost_center] = frappe.db.get_value(
					"Cost Center", self.cost_center, "company")

			return self.cost_center_company[self.cost_center]

		if self.cost_center and _get_cost_center_company() != self.company:
			frappe.throw(_("{0} {1}: Cost Center {2} does not belong to Company {3}")
				.format(self.voucher_type, self.voucher_no, self.cost_center, self.company))

	def validate_party(self):
		validate_party_frozen_disabled(self.party_type, self.party)

	def validate_currency(self):
		company_currency = erpnext.get_company_currency(self.company)
		account_currency = get_account_currency(self.account)

		if not self.account_currency:
			self.account_currency = company_currency

		if account_currency != self.account_currency:
			frappe.throw(_("{0} {1}: Accounting Entry for {2} can only be made in currency: {3}")
				.format(self.voucher_type, self.voucher_no, self.account,
				(account_currency or company_currency)), InvalidAccountCurrency)

		if self.party_type and self.party:
			validate_party_gle_currency(self.party_type, self.party, self.company, self.account_currency)


	def validate_and_set_fiscal_year(self):
		if not self.fiscal_year:
			self.fiscal_year = get_fiscal_year(self.posting_date, company=self.company)[0]


def validate_balance_type(account, adv_adj=False):
	if not adv_adj and account:
		balance_must_be = frappe.db.get_value("Account", account, "balance_must_be")
		if balance_must_be:
			balance = frappe.db.sql("""select sum(debit) - sum(credit)
				from `tabGL Entry` where account = %s""", account)[0][0]

			if (balance_must_be=="Debit" and flt(balance) < 0) or \
				(balance_must_be=="Credit" and flt(balance) > 0):
				frappe.throw(_("Balance for Account {0} must always be {1}").format(account, _(balance_must_be)))

def check_freezing_date(posting_date, adv_adj=False):
	"""
		Nobody can do GL Entries where posting date is before freezing date
		except authorized person
	"""
	if not adv_adj:
		acc_frozen_upto = frappe.db.get_value('Accounts Settings', None, 'acc_frozen_upto')
		if acc_frozen_upto:
			frozen_accounts_modifier = frappe.db.get_value( 'Accounts Settings', None,'frozen_accounts_modifier')
			if getdate(posting_date) <= getdate(acc_frozen_upto) \
					and not frozen_accounts_modifier in frappe.get_roles():
				frappe.throw(_("You are not authorized to add or update entries before {0}").format(formatdate(acc_frozen_upto)))

def update_outstanding_amt(account, party_type, party, against_voucher_type, against_voucher, on_cancel=False):
	if party_type and party:
		party_condition = " and party_type={0} and party={1}"\
			.format(frappe.db.escape(party_type), frappe.db.escape(party))
	else:
		party_condition = ""

	# get final outstanding amt
	bal = flt(frappe.db.sql("""
		select sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where against_voucher_type=%s and against_voucher=%s
		and account = %s {0}""".format(party_condition),
		(against_voucher_type, against_voucher, account))[0][0] or 0.0)

	if against_voucher_type == 'Purchase Invoice':
		bal = -bal
	elif against_voucher_type == "Journal Entry":
		against_voucher_amount = flt(frappe.db.sql("""
			select sum(debit_in_account_currency) - sum(credit_in_account_currency)
			from `tabGL Entry` where voucher_type = 'Journal Entry' and voucher_no = %s
			and account = %s and (against_voucher is null or against_voucher='') {0}"""
			.format(party_condition), (against_voucher, account))[0][0])

		if not against_voucher_amount:
			frappe.throw(_("Against Journal Entry {0} is already adjusted against some other voucher")
				.format(against_voucher))

		bal = against_voucher_amount + bal
		if against_voucher_amount < 0:
			bal = -bal

		# Validation : Outstanding can not be negative for JV
		if bal < 0 and not on_cancel:
			frappe.throw(_("Outstanding for {0} cannot be less than zero ({1})").format(against_voucher, fmt_money(bal)))

	# Update outstanding amt on against voucher
	if against_voucher_type in ["Sales Invoice", "Purchase Invoice", "Fees"]:
		ref_doc = frappe.get_doc(against_voucher_type, against_voucher)
		ref_doc.db_set('outstanding_amount', bal)
		ref_doc.set_status(update=True)

def validate_frozen_account(account, adv_adj=None):
	frozen_account = frappe.db.get_value("Account", account, "freeze_account")
	if frozen_account == 'Yes' and not adv_adj:
		frozen_accounts_modifier = frappe.db.get_value( 'Accounts Settings', None,
			'frozen_accounts_modifier')

		if not frozen_accounts_modifier:
			frappe.throw(_("Account {0} is frozen").format(account))
		elif frozen_accounts_modifier not in frappe.get_roles():
			frappe.throw(_("Not authorized to edit frozen Account {0}").format(account))

def update_against_account(voucher_type, voucher_no):
	entries = frappe.db.get_all("GL Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
		fields=["name", "party", "against", "debit", "credit", "account"])

	accounts_debited, accounts_credited = [], []
	for d in entries:
		if flt(d.debit > 0): accounts_debited.append(d.party or d.account)
		if flt(d.credit) > 0: accounts_credited.append(d.party or d.account)

	for d in entries:
		if flt(d.debit > 0):
			new_against = ", ".join(list(set(accounts_credited)))
		if flt(d.credit > 0):
			new_against = ", ".join(list(set(accounts_debited)))

		if d.against != new_against:
			frappe.db.set_value("GL Entry", d.name, "against", new_against)


def rename_gle_sle_docs():
	for doctype in ["GL Entry", "Stock Ledger Entry"]:
		rename_temporarily_named_docs(doctype)

def rename_temporarily_named_docs(doctype):
	"""Rename temporarily named docs using autoname options"""
	docs_to_rename = frappe.get_all(doctype, {"to_rename": "1"}, order_by="creation")
	for doc in docs_to_rename:
		oldname = doc.name
		set_name_from_naming_options(frappe.get_meta(doctype).autoname, doc)
		newname = doc.name
		frappe.db.sql("""UPDATE `tab{}` SET name = %s, to_rename = 0 where name = %s""".format(doctype), (newname, oldname))
