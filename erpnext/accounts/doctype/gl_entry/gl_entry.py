# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, fmt_money, getdate, formatdate, cint
from frappe.model.document import Document
from frappe.model.naming import set_name_from_naming_options
from frappe.model.meta import get_field_precision
from erpnext.accounts.party import validate_party_gle_currency, validate_party_frozen_disabled
from erpnext.accounts.utils import get_account_currency, get_balance_on_voucher, get_fiscal_year
from erpnext.exceptions import InvalidAccountCurrency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_checks_for_pl_and_bs_accounts
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_all_sales_invoice_receivable_accounts

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
		self.pl_must_have_cost_center()
		self.validate_cost_center()

		if not self.flags.from_repost:
			self.check_pl_account()
			self.validate_party()
			self.validate_currency()

	def on_update_with_args(self, adv_adj, from_repost=False):
		if not from_repost:
			self.validate_account_details(adv_adj)
			self.validate_dimensions_for_pl_and_bs()
			check_freezing_date(self.posting_date, adv_adj)

		validate_frozen_account(self.account, adv_adj)
		validate_balance_type(self.account, adv_adj)

	def check_mandatory(self):
		mandatory = ['account','voucher_type','voucher_no','company']
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(_(self.meta.get_label(k))))

		if self.party and not self.party_type:
			frappe.throw(_("Party is set but Party Type is not provided"))
		if self.party_type and not self.party:
			frappe.throw(_("Party Type is set but Party is not provided"))
		if self.against_voucher and not self.against_voucher_type:
			frappe.throw(_("Against Voucher is set but Against Voucher Type is not provided"))
		if self.against_voucher_type and not self.against_voucher:
			frappe.throw(_("Against Voucher is set but Against Voucher Type is not provided"))

		account_type = frappe.db.get_value("Account", self.account, "account_type")
		if not (self.party_type and self.party):
			if account_type == "Receivable":
				frappe.throw(_("{0} {1}: Party is required against Receivable account {2}")
					.format(self.voucher_type, self.voucher_no, self.account))
			elif account_type == "Payable":
				frappe.throw(_("{0} {1}: Party is required against Payable account {2}")
					.format(self.voucher_type, self.voucher_no, self.account))

		if self.party and account_type not in ('Receivable', 'Payable'):
			frappe.throw(_("{0} {1}: Party cannot be set for Account {2} because it is neither a Receivable or Payable account")
				.format(self.voucher_type, self.voucher_no, self.account))

		# Zero value transaction is not allowed
		if not (flt(self.debit, self.precision("debit")) or flt(self.credit, self.precision("credit"))):
			frappe.throw(_("{0} {1}: Either debit or credit amount is required for {2}")
				.format(self.voucher_type, self.voucher_no, self.account))

	def pl_must_have_cost_center(self):
		if frappe.db.get_value("Account", self.account, "report_type") == "Profit and Loss":
			if not self.cost_center and self.voucher_type != 'Period Closing Voucher':
				frappe.throw(_("{0} {1}: Cost Center is required for 'Profit and Loss' account {2}. Please set up a default Cost Center for the Company.")
					.format(self.voucher_type, self.voucher_no, self.account))
		else:
			from erpnext.accounts.utils import get_allow_cost_center_in_entry_of_bs_account, get_allow_project_in_entry_of_bs_account
			if not get_allow_cost_center_in_entry_of_bs_account() and self.cost_center:
				self.cost_center = None
			if not get_allow_project_in_entry_of_bs_account() and self.project:
				self.project = None

	def validate_dimensions_for_pl_and_bs(self):
		account_type = frappe.db.get_value("Account", self.account, "report_type")

		accounting_dimensions = get_checks_for_pl_and_bs_accounts()
		if accounting_dimensions:
			mandatory_for_account = frappe.get_all("Mandatory Accounting Dimension",
				filters={'parenttype': 'Account', 'parent': self.account}, fields=['accounting_dimension'])
			mandatory_for_account = [d.accounting_dimension for d in mandatory_for_account]

			for dimension in get_checks_for_pl_and_bs_accounts():
				if dimension.name in mandatory_for_account and self.company == dimension.company and not dimension.disabled:
					frappe.throw(_("Accounting Dimension <b>{0}</b> is required for Account <b>{1}</b>.")
						.format(dimension.label, self.account))

				if account_type == "Profit and Loss" \
					and self.company == dimension.company and dimension.mandatory_for_pl and not dimension.disabled:
					if not self.get(dimension.fieldname):
						frappe.throw(_("Accounting Dimension <b>{0}</b> is required for 'Profit and Loss' account {1}.")
							.format(dimension.label, self.account))

				if account_type == "Balance Sheet" \
					and self.company == dimension.company and dimension.mandatory_for_bs and not dimension.disabled:
					if not self.get(dimension.fieldname):
						frappe.throw(_("Accounting Dimension <b>{0}</b> is required for 'Balance Sheet' account {1}.")
							.format(dimension.label, self.account))


	def check_pl_account(self):
		if self.is_opening=='Yes' and \
				frappe.db.get_value("Account", self.account, "report_type")=="Profit and Loss" and \
				self.voucher_type not in ['Purchase Invoice', 'Sales Invoice', 'Journal Entry']:
			frappe.throw(_("{0} {1}: 'Profit and Loss' type account {2} not allowed in Opening Entry")
				.format(self.voucher_type, self.voucher_no, self.account))

	def validate_account_details(self, adv_adj):
		"""Account must be ledger, active and not freezed"""

		ret = frappe.db.sql("""select is_group, docstatus, company
			from tabAccount where name=%s""", self.account, as_dict=1)[0]

		if ret.is_group==1:
			frappe.throw(_('''{0} {1}: Account {2} is a Group Account and group accounts cannot be used in
				transactions''').format(self.voucher_type, self.voucher_no, self.account))

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

		def _check_is_group():
			return cint(frappe.get_cached_value('Cost Center', self.cost_center, 'is_group'))

		if self.cost_center and _get_cost_center_company() != self.company:
			frappe.throw(_("{0} {1}: Cost Center {2} does not belong to Company {3}")
				.format(self.voucher_type, self.voucher_no, self.cost_center, self.company))

		if self.cost_center and _check_is_group():
			frappe.throw(_("""{0} {1}: Cost Center {2} is a group cost center and group cost centers cannot
				be used in transactions""").format(self.voucher_type, self.voucher_no, frappe.bold(self.cost_center)))

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

def update_outstanding_amt(voucher_type, voucher_no, account, party_type, party, on_cancel=False):
	# Update outstanding amt on against voucher

	dr_or_cr = None
	include_original_references = False

	if voucher_type in ["Sales Invoice", "Purchase Invoice", "Landed Cost Voucher", "Fees", "Expense Claim"]:
		fieldname = "outstanding_amount"
	elif voucher_type == "Employee Advance":
		fieldname = "balance_amount"
		include_original_references = True
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
	elif voucher_type in ("Sales Order", "Purchase Order"):
		fieldname = "advance_paid"
		include_original_references = True
		if voucher_type == "Sales Order":
			dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		else:
			dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
	else:
		return

	if voucher_type == "Sales Invoice":
		receivable_accounts = get_all_sales_invoice_receivable_accounts(voucher_no)
		if receivable_accounts:
			account = list(set([account] + receivable_accounts))

	bal = get_balance_on_voucher(voucher_type, voucher_no, party_type, party, account,
		dr_or_cr=dr_or_cr, include_original_references=include_original_references)
	ref_doc = frappe.get_doc(voucher_type, voucher_no)
	ref_doc.db_set(fieldname, bal)

	if voucher_type == "Employee Advance":
		ref_doc.set_payment_and_claimed_amount(update=True)

	ref_doc.set_status(update=True)
	ref_doc.notify_update()

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
		fields=["name", "party", "against", "debit", "credit", "account", "company"])

	if not entries:
		return
	company_currency = erpnext.get_company_currency(entries[0].company)
	precision = get_field_precision(frappe.get_meta("GL Entry")
			.get_field("debit"), company_currency)

	accounts_debited, accounts_credited = [], []
	for d in entries:
		if flt(d.debit, precision) > 0: accounts_debited.append(d.party or d.account)
		if flt(d.credit, precision) > 0: accounts_credited.append(d.party or d.account)

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
		frappe.db.sql("""UPDATE `tab{}` SET name = %s, to_rename = 0 where name = %s""".format(doctype), (newname, oldname))
