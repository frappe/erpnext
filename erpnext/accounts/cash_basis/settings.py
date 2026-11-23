# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Company settings of the accounting method, and the guards of the cash basis on documents:
the unapplied cash accounts, and the Journal Entry field cash_basis_treatment."""

import frappe
from frappe import _

from erpnext.accounts.cash_basis import (
	ACCRUAL,
	CASH,
	get_cash_method_countries,
	is_cash_method_available_for_country,
)
from erpnext.accounts.doctype.account.account import get_root_company

UNAPPLIED_ACCOUNTS = {
	# Company field: (account name, root type)
	"unapplied_cash_receipts_account": ("Unapplied Cash Receipts", "Income"),
	"unapplied_cash_payments_account": ("Unapplied Cash Payments", "Expense"),
}


class CompanyAccountingMethod:
	"""Validation of the accounting method fields of one Company document."""

	def __init__(self, company_doc):
		self.doc = company_doc

	def validate(self):
		self.reset_on_country_change()
		self.validate_country()
		if self.needs_unapplied_accounts() and not self.doc.is_new():
			# A new company has no chart yet. on_update sets the accounts for it.
			self.set_missing_unapplied_accounts()
			self.validate_unapplied_accounts()
		self.validate_dedicated_unapplied_accounts()

	def on_update(self):
		if self.needs_unapplied_accounts() and self.has_missing_unapplied_accounts():
			self.set_missing_unapplied_accounts(save=True)

	def reset_on_country_change(self):
		if self.doc.is_new() or self.doc.accounting_method != CASH:
			return
		if is_cash_method_available_for_country(self.doc.country):
			return
		if not self.doc.has_value_changed("country"):
			return

		self.doc.accounting_method = ACCRUAL
		frappe.msgprint(
			_(
				"The country {0} cannot use the accounting method Cash. The accounting method is now Accrual."
			).format(frappe.bold(self.doc.country)),
			alert=True,
		)

	def validate_country(self):
		if self.doc.accounting_method != CASH:
			return
		if is_cash_method_available_for_country(self.doc.country):
			return
		countries = get_cash_method_countries()
		message = (
			_(
				"The accounting method Cash is available only for a company in these countries: {0}. "
				"Select the accounting method Accrual."
			).format(", ".join(countries))
			if countries
			else _("The accounting method Cash is not available. Select the accounting method Accrual.")
		)
		frappe.throw(message, title=_("Accounting Method Not Available"))

	def needs_unapplied_accounts(self) -> bool:
		from erpnext.accounts.cash_basis.calculation import UNAPPLIED_INCOME_AND_EXPENSE

		return (
			self.doc.accounting_method == CASH
			and self.doc.unapplied_cash_treatment == UNAPPLIED_INCOME_AND_EXPENSE
		)

	def has_missing_unapplied_accounts(self) -> bool:
		return any(not self.doc.get(fieldname) for fieldname in UNAPPLIED_ACCOUNTS)

	def set_missing_unapplied_accounts(self, save=False):
		for fieldname, (account_name, root_type) in UNAPPLIED_ACCOUNTS.items():
			if self.doc.get(fieldname):
				continue
			account = get_or_create_unapplied_account(
				self.doc, account_name, root_type, in_company_insert=bool(self.doc.flags.in_insert)
			)
			if save:
				self.doc.db_set(fieldname, account)
			else:
				self.doc.set(fieldname, account)

	def validate_unapplied_accounts(self):
		# validate_default_accounts of Company checks the root type of each account.
		for fieldname in UNAPPLIED_ACCOUNTS:
			if not self.doc.get(fieldname):
				label = self.doc.meta.get_translated_label(fieldname)
				frappe.throw(
					_("{0} is mandatory when the accounting method is Cash.").format(frappe.bold(label)),
					title=_("Missing Account"),
				)

	def validate_dedicated_unapplied_accounts(self):
		"""An unapplied account must be a dedicated account, because no voucher can post to it."""
		other_defaults = self.get_other_default_accounts()
		for fieldname in UNAPPLIED_ACCOUNTS:
			account = self.doc.get(fieldname)
			if not account:
				continue

			label = self.doc.meta.get_translated_label(fieldname)
			if account in other_defaults:
				other_label = self.doc.meta.get_translated_label(other_defaults[account])
				frappe.throw(
					_(
						"The account {0} is set in {1} and in {2}. An unapplied cash account must be a dedicated account."
					).format(frappe.bold(account), frappe.bold(label), frappe.bold(other_label)),
					title=_("Account Not Permitted"),
				)
			is_changed = self.doc.is_new() or self.doc.has_value_changed(fieldname)
			if is_changed and has_postings(account):
				frappe.throw(
					_(
						"{0}: the account {1} has postings. Select a dedicated account with no postings."
					).format(frappe.bold(label), frappe.bold(account)),
					title=_("Account Not Permitted"),
				)

	def get_other_default_accounts(self) -> dict[str, str]:
		"""Map of each other default account of the company to its field."""
		return {
			self.doc.get(df.fieldname): df.fieldname
			for df in self.doc.meta.get_link_fields()
			if df.options == "Account"
			and df.fieldname not in UNAPPLIED_ACCOUNTS
			and self.doc.get(df.fieldname)
		}


def get_or_create_unapplied_account(
	company_doc, account_name: str, root_type: str, in_company_insert: bool = False
) -> str | None:
	existing = frappe.db.get_value(
		"Account",
		{"company": company_doc.name, "account_name": account_name},
		["name", "is_group", "root_type", "disabled"],
		as_dict=True,
	)
	if existing:
		if existing.is_group or existing.disabled or existing.root_type != root_type:
			frappe.throw(
				_(
					"The account {0} exists, but it is not an enabled ledger account with root type {1}. "
					"Select an unapplied cash account in the company."
				).format(frappe.bold(existing.name), get_root_type_label(root_type)),
				title=_("Account Not Permitted"),
			)
		# An account with postings is not dedicated. The validation of the company refuses it.
		return existing.name

	if not in_company_insert:
		validate_root_company_has_account(company_doc, account_name)

	parent_account = get_root_group_account(company_doc.name, root_type)
	if not parent_account:
		return None

	account = frappe.new_doc("Account")
	account.update(
		{
			"account_name": account_name,
			"company": company_doc.name,
			"parent_account": parent_account,
			"is_group": 0,
			"account_currency": company_doc.default_currency,
		}
	)
	# While a company is inserted, its chart is new. create_default_accounts skips the root
	# company rules for the same reason, also for a new child company. Later, the rules apply.
	previous_flag = frappe.local.flags.ignore_root_company_validation
	if in_company_insert:
		frappe.local.flags.ignore_root_company_validation = True
	try:
		account.insert(ignore_permissions=True)
	finally:
		frappe.local.flags.ignore_root_company_validation = previous_flag

	return account.name


def validate_root_company_has_account(company_doc, account_name: str):
	"""Account refuses a new account in a child company that its root company does not have."""
	root_company = get_root_company(company_doc.name)
	if not root_company:
		return
	# Account reads the saved value, so this check reads it too.
	if frappe.get_cached_value("Company", company_doc.name, "allow_account_creation_against_child_company"):
		return
	if frappe.db.exists("Account", {"company": root_company[0], "account_name": account_name}):
		return

	frappe.throw(
		_(
			"The company {0} is a child of the company {1}. Create the account {2} in {1} first. "
			"Then save {0} again."
		).format(frappe.bold(company_doc.name), frappe.bold(root_company[0]), frappe.bold(account_name)),
		title=_("Account Missing in Root Company"),
	)


def get_root_group_account(company: str, root_type: str) -> str | None:
	roots = frappe.get_all(
		"Account",
		filters={
			"company": company,
			"root_type": root_type,
			"is_group": 1,
			"parent_account": ("is", "not set"),
		},
		order_by="lft",
		limit=1,
		pluck="name",
	)
	return roots[0] if roots else None


def get_root_type_label(root_type: str) -> str:
	# The keys are the root types of UNAPPLIED_ACCOUNTS.
	return {"Income": _("Income"), "Expense": _("Expense")}[root_type]


def has_postings(account: str) -> bool:
	return bool(frappe.db.exists("GL Entry", {"account": account, "is_cancelled": 0}))


def get_unapplied_settings(company: str) -> dict:
	"""The keyword arguments of the calculation for the unapplied cash of the company."""
	treatment, receipts, payments = frappe.get_cached_value(
		"Company",
		company,
		["unapplied_cash_treatment", "unapplied_cash_receipts_account", "unapplied_cash_payments_account"],
	)
	return {
		"unapplied_treatment": treatment,
		"unapplied_accounts": {"Customer": receipts, "Supplier": payments},
	}


def validate_gl_account_is_not_unapplied(gl_entry):
	"""No voucher can post to an unapplied cash account. Only the cash basis reports use it."""
	unapplied_accounts = frappe.get_cached_value("Company", gl_entry.company, list(UNAPPLIED_ACCOUNTS))
	if gl_entry.account in (unapplied_accounts or ()):
		frappe.throw(
			_(
				"{0} {1}: the account {2} is an unapplied cash account. Only the cash basis reports use it. "
				"Select a different account."
			).format(gl_entry.voucher_type, gl_entry.voucher_no, frappe.bold(gl_entry.account)),
			title=_("Account Not Permitted"),
		)


def validate_journal_entry_treatment(doc, after_submit=False):
	"""The Journal Entry field cash_basis_treatment (section 6.5).

	The field sets the class of an entry with rows other than party rows. A Journal Entry with
	only party rows follows rule 4, and an entry with a Bank or Cash row pays cash, so it cannot
	be a non-cash adjustment. A change after submit changes the cash basis result of its posting
	date, so it follows the freeze of the accounts, as a ledger change does.
	"""
	from erpnext.accounts.cash_basis.settlements import AUTOMATIC, NON_CASH_ADJUSTMENT

	treatment = doc.get("cash_basis_treatment")
	if treatment and treatment != AUTOMATIC:
		accounts = [row.account for row in doc.get("accounts") or [] if row.account]
		account_types = (
			frappe.get_all("Account", filters={"name": ("in", accounts)}, pluck="account_type")
			if accounts
			else []
		)
		if account_types and all(t in ("Receivable", "Payable") for t in account_types):
			frappe.throw(
				_(
					"A Journal Entry with only party rows cannot have a cash basis treatment. Set it to Automatic."
				),
				title=_("Invalid Cash Basis Treatment"),
			)
		if treatment == NON_CASH_ADJUSTMENT and {"Bank", "Cash"} & set(account_types):
			frappe.throw(
				_("A Journal Entry with a Bank or Cash row cannot be a {0}.").format(
					frappe.bold(_("Non-cash Adjustment"))
				),
				title=_("Invalid Cash Basis Treatment"),
			)
	if after_submit and doc.has_value_changed("cash_basis_treatment"):
		from erpnext.accounts.services.gl_validator import check_freezing_date

		check_freezing_date(doc.posting_date, doc.company)
