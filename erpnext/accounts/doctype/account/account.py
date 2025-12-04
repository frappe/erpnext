# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, throw
from frappe.utils import add_to_date, cint, cstr, pretty_date
from frappe.utils.nestedset import NestedSet, get_ancestors_of, get_descendants_of

import erpnext


class RootNotEditable(frappe.ValidationError):
	pass


class BalanceMismatchError(frappe.ValidationError):
	pass


class InvalidAccountMergeError(frappe.ValidationError):
	pass


class Account(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_category: DF.Link | None
		account_currency: DF.Link | None
		account_name: DF.Data
		account_number: DF.Data | None
		account_type: DF.Literal[
			"",
			"Accumulated Depreciation",
			"Asset Received But Not Billed",
			"Bank",
			"Cash",
			"Chargeable",
			"Capital Work in Progress",
			"Cost of Goods Sold",
			"Current Asset",
			"Current Liability",
			"Depreciation",
			"Direct Expense",
			"Direct Income",
			"Equity",
			"Expense Account",
			"Expenses Included In Asset Valuation",
			"Expenses Included In Valuation",
			"Fixed Asset",
			"Income Account",
			"Indirect Expense",
			"Indirect Income",
			"Liability",
			"Payable",
			"Receivable",
			"Round Off",
			"Round Off for Opening",
			"Stock",
			"Stock Adjustment",
			"Stock Received But Not Billed",
			"Service Received But Not Billed",
			"Tax",
			"Temporary",
		]
		balance_must_be: DF.Literal["", "Debit", "Credit"]
		company: DF.Link
		disabled: DF.Check
		freeze_account: DF.Literal["No", "Yes"]
		include_in_gross: DF.Check
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Data | None
		parent_account: DF.Link
		report_type: DF.Literal["", "Balance Sheet", "Profit and Loss"]
		rgt: DF.Int
		root_type: DF.Literal["", "Asset", "Liability", "Income", "Expense", "Equity"]
		tax_rate: DF.Float
	# end: auto-generated types

	nsm_parent_field = "parent_account"

	def on_update(self):
		if frappe.local.flags.ignore_update_nsm:
			return
		else:
			super().on_update()

	def onload(self):
		role_allowed_for_frozen_entries = frappe.db.get_value(
			"Company", self.company, "role_allowed_for_frozen_entries"
		)
		if not role_allowed_for_frozen_entries or role_allowed_for_frozen_entries in frappe.get_roles():
			self.set_onload("can_freeze_account", True)

	def autoname(self):
		from erpnext.accounts.utils import get_autoname_with_number

		self.name = get_autoname_with_number(self.account_number, self.account_name, self.company)

	def validate(self):
		if frappe.local.flags.allow_unverified_charts:
			return
		self.validate_parent()
		self.validate_parent_child_account_type()
		self.validate_root_details()
		self.validate_account_number()
		self.validate_disabled()
		self.validate_group_or_ledger()
		self.set_root_and_report_type()
		self.validate_mandatory()
		self.validate_frozen_accounts_modifier()
		self.validate_balance_must_be_debit_or_credit()
		self.validate_account_currency()
		self.validate_root_company_and_sync_account_to_children()
		self.validate_receivable_payable_account_type()

	def validate_parent_child_account_type(self):
		if self.parent_account:
			if self.account_type in [
				"Direct Income",
				"Indirect Income",
				"Current Asset",
				"Current Liability",
				"Direct Expense",
				"Indirect Expense",
			]:
				parent_account_type = frappe.db.get_value("Account", self.parent_account, ["account_type"])
				if parent_account_type == self.account_type:
					throw(_("Only Parent can be of type {0}").format(self.account_type))

	def validate_parent(self):
		"""Fetch Parent Details and validate parent account"""
		if self.parent_account:
			par = frappe.get_cached_value(
				"Account", self.parent_account, ["name", "is_group", "company"], as_dict=1
			)
			if not par:
				throw(
					_("Account {0}: Parent account {1} does not exist").format(self.name, self.parent_account)
				)
			elif par.name == self.name:
				throw(_("Account {0}: You can not assign itself as parent account").format(self.name))
			elif not par.is_group:
				throw(
					_("Account {0}: Parent account {1} can not be a ledger").format(
						self.name, self.parent_account
					)
				)
			elif par.company != self.company:
				throw(
					_("Account {0}: Parent account {1} does not belong to company: {2}").format(
						self.name, self.parent_account, self.company
					)
				)

	def set_root_and_report_type(self):
		if self.parent_account:
			par = frappe.get_cached_value(
				"Account", self.parent_account, ["report_type", "root_type"], as_dict=1
			)

			if par.report_type:
				self.report_type = par.report_type
			if par.root_type:
				self.root_type = par.root_type

		if cint(self.is_group):
			db_value = self.get_doc_before_save()
			if db_value:
				if self.report_type != db_value.report_type:
					frappe.db.sql(
						"update `tabAccount` set report_type=%s where lft > %s and rgt < %s",
						(self.report_type, self.lft, self.rgt),
					)
				if self.root_type != db_value.root_type:
					frappe.db.sql(
						"update `tabAccount` set root_type=%s where lft > %s and rgt < %s",
						(self.root_type, self.lft, self.rgt),
					)

		if self.root_type and not self.report_type:
			self.report_type = (
				"Balance Sheet" if self.root_type in ("Asset", "Liability", "Equity") else "Profit and Loss"
			)

	def validate_receivable_payable_account_type(self):
		doc_before_save = self.get_doc_before_save()
		receivable_payable_types = ["Receivable", "Payable"]
		if (
			doc_before_save
			and doc_before_save.account_type in receivable_payable_types
			and doc_before_save.account_type != self.account_type
		):
			# check for ledger entries
			if frappe.db.get_all("GL Entry", filters={"account": self.name, "is_cancelled": 0}, limit=1):
				msg = _(
					"There are ledger entries against this account. Changing {0} to non-{1} in live system will cause incorrect output in 'Accounts {2}' report"
				).format(
					frappe.bold(_("Account Type")), doc_before_save.account_type, doc_before_save.account_type
				)
				frappe.msgprint(msg)
				self.add_comment("Comment", msg)

	def validate_root_details(self):
		doc_before_save = self.get_doc_before_save()

		if doc_before_save and not doc_before_save.parent_account:
			throw(_("Root cannot be edited."), RootNotEditable)

		if not self.parent_account and not cint(self.is_group):
			throw(_("The root account {0} must be a group").format(frappe.bold(self.name)))

	def validate_root_company_and_sync_account_to_children(self):
		# ignore validation while creating new compnay or while syncing to child companies
		if frappe.local.flags.ignore_root_company_validation or self.flags.ignore_root_company_validation:
			return
		ancestors = get_root_company(self.company)
		if ancestors:
			if frappe.get_cached_value(
				"Company", self.company, "allow_account_creation_against_child_company"
			):
				return
			if not frappe.db.get_value(
				"Account", {"account_name": self.account_name, "company": ancestors[0]}, "name"
			):
				frappe.throw(_("Please add the account to root level Company - {}").format(ancestors[0]))
		elif self.parent_account:
			descendants = get_descendants_of("Company", self.company)
			if not descendants:
				return
			parent_acc_name_map = {}
			parent_acc_name, parent_acc_number = frappe.get_cached_value(
				"Account", self.parent_account, ["account_name", "account_number"]
			)
			filters = {
				"company": ["in", descendants],
				"account_name": parent_acc_name,
			}
			if parent_acc_number:
				filters["account_number"] = parent_acc_number

			for d in frappe.db.get_values(
				"Account", filters=filters, fieldname=["company", "name"], as_dict=True
			):
				parent_acc_name_map[d["company"]] = d["name"]

			if not parent_acc_name_map:
				return

			self.create_account_for_child_company(parent_acc_name_map, descendants, parent_acc_name)

	def validate_disabled(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or cint(doc_before_save.disabled) == cint(self.disabled):
			return

		if cint(self.disabled):
			self.validate_default_accounts_in_company()

	def validate_group_or_ledger(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or cint(doc_before_save.is_group) == cint(self.is_group):
			return

		if self.check_gle_exists():
			throw(_("Account with existing transaction cannot be converted to ledger"))
		elif cint(self.is_group):
			if self.account_type and not self.flags.exclude_account_type_check:
				throw(_("Cannot covert to Group because Account Type is selected."))
			self.validate_default_accounts_in_company()
		elif self.check_if_child_exists():
			throw(_("Account with child nodes cannot be set as ledger"))

	def validate_default_accounts_in_company(self):
		default_account_fields = get_company_default_account_fields()

		company_default_accounts = frappe.db.get_value(
			"Company", self.company, list(default_account_fields.keys()), as_dict=1
		)

		msg = _("Account {0} cannot be disabled as it is already set as {1} for {2}.")

		if not self.disabled:
			msg = _("Account {0} cannot be converted to Group as it is already set as {1} for {2}.")

		for d in default_account_fields:
			if company_default_accounts.get(d) == self.name:
				throw(
					msg.format(
						frappe.bold(self.name),
						frappe.bold(default_account_fields.get(d)),
						frappe.bold(self.company),
					)
				)

	def validate_frozen_accounts_modifier(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or doc_before_save.freeze_account == self.freeze_account:
			return

		role_allowed_for_frozen_entries = frappe.get_cached_value(
			"Company", self.company, "role_allowed_for_frozen_entries"
		)
		if not role_allowed_for_frozen_entries or role_allowed_for_frozen_entries not in frappe.get_roles():
			throw(_("You are not authorized to set Frozen value"))

	def validate_balance_must_be_debit_or_credit(self):
		from erpnext.accounts.utils import get_balance_on

		if not self.get("__islocal") and self.balance_must_be:
			account_balance = get_balance_on(self.name)

			if account_balance > 0 and self.balance_must_be == "Credit":
				frappe.throw(
					_(
						"Account balance already in Debit, you are not allowed to set 'Balance Must Be' as 'Credit'"
					)
				)
			elif account_balance < 0 and self.balance_must_be == "Debit":
				frappe.throw(
					_(
						"Account balance already in Credit, you are not allowed to set 'Balance Must Be' as 'Debit'"
					)
				)

	def validate_account_currency(self):
		self.currency_explicitly_specified = True

		if not self.account_currency:
			self.account_currency = frappe.get_cached_value("Company", self.company, "default_currency")
			self.currency_explicitly_specified = False

		gl_currency = frappe.db.get_value(
			"GL Entry", {"account": self.name, "is_cancelled": 0}, "account_currency"
		)

		if gl_currency and self.account_currency != gl_currency:
			if frappe.db.get_value("GL Entry", {"account": self.name}):
				frappe.throw(_("Currency can not be changed after making entries using some other currency"))

	def validate_account_number(self, account_number=None):
		if not account_number:
			account_number = self.account_number

		if account_number:
			account_with_same_number = frappe.db.get_value(
				"Account",
				{"account_number": account_number, "company": self.company, "name": ["!=", self.name]},
			)
			if account_with_same_number:
				frappe.throw(
					_("Account Number {0} already used in account {1}").format(
						account_number, account_with_same_number
					)
				)

	def create_account_for_child_company(self, parent_acc_name_map, descendants, parent_acc_name):
		for company in descendants:
			company_bold = frappe.bold(company)
			parent_acc_name_bold = frappe.bold(parent_acc_name)
			if not parent_acc_name_map.get(company):
				frappe.throw(
					_(
						"While creating account for Child Company {0}, parent account {1} not found. Please create the parent account in corresponding COA"
					).format(company_bold, parent_acc_name_bold),
					title=_("Account Not Found"),
				)

			# validate if parent of child company account to be added is a group
			if frappe.get_cached_value(
				"Account", self.parent_account, "is_group"
			) and not frappe.get_cached_value("Account", parent_acc_name_map[company], "is_group"):
				msg = _(
					"While creating account for Child Company {0}, parent account {1} found as a ledger account."
				).format(company_bold, parent_acc_name_bold)
				msg += "<br><br>"
				msg += _(
					"Please convert the parent account in corresponding child company to a group account."
				)
				frappe.throw(msg, title=_("Invalid Parent Account"))

			filters = {"account_name": self.account_name, "company": company}

			if self.account_number:
				filters["account_number"] = self.account_number

			child_account = frappe.db.get_value("Account", filters, "name")
			if not child_account:
				doc = frappe.copy_doc(self)
				doc.flags.ignore_root_company_validation = True
				doc.update(
					{
						"company": company,
						# parent account's currency should be passed down to child account's curreny
						# if currency explicitly specified by user, child will inherit. else, default currency will be used.
						"account_currency": self.account_currency
						if self.currency_explicitly_specified
						else erpnext.get_company_currency(company),
						"parent_account": parent_acc_name_map[company],
					}
				)

				doc.save()
				frappe.msgprint(_("Account {0} is added in the child company {1}").format(doc.name, company))
			elif child_account:
				# update the parent company's value in child companies
				doc = frappe.get_doc("Account", child_account)
				parent_value_changed = False
				for field in ["account_type", "freeze_account", "balance_must_be"]:
					if doc.get(field) != self.get(field):
						parent_value_changed = True
						doc.set(field, self.get(field))

				if parent_value_changed:
					doc.save()

	@frappe.whitelist()
	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			throw(_("Account with child nodes cannot be converted to ledger"))
		elif self.check_gle_exists():
			throw(_("Account with existing transaction cannot be converted to ledger"))
		else:
			self.is_group = 0
			self.save()
			return 1

	@frappe.whitelist()
	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be converted to group."))
		elif self.account_type and not self.flags.exclude_account_type_check:
			throw(_("Cannot convert to Group because Account Type is selected."))
		else:
			self.is_group = 1
			self.save()
			return 1

	# Check if any previous balance exists
	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"account": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql(
			"""select name from `tabAccount` where parent_account = %s
			and docstatus != 2""",
			self.name,
		)

	def validate_mandatory(self):
		if not self.root_type:
			throw(_("Root Type is mandatory"))

		if not self.report_type:
			throw(_("Report Type is mandatory"))

	def on_trash(self):
		# checks gl entries and if child exists
		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be deleted"))

		super().on_trash(True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_parent_account(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""select name from tabAccount
		where is_group = 1 and docstatus != 2 and company = {}
		and {} like {} order by name limit {} offset {}""".format("%s", searchfield, "%s", "%s", "%s"),
		(filters["company"], "%%%s%%" % txt, page_len, start),
		as_list=1,
	)


def get_account_currency(account):
	"""Helper function to get account currency"""
	if not account:
		return

	def generator():
		account_currency, company = frappe.get_cached_value(
			"Account", account, ["account_currency", "company"]
		)
		if not account_currency:
			account_currency = frappe.get_cached_value("Company", company, "default_currency")

		return account_currency

	return frappe.local_cache("account_currency", account, generator)


def on_doctype_update():
	frappe.db.add_index("Account", ["lft", "rgt"])


def get_account_autoname(account_number, account_name, company):
	# first validate if company exists
	company = frappe.get_cached_value("Company", company, ["abbr", "name"], as_dict=True)
	if not company:
		frappe.throw(_("Company {0} does not exist").format(company))

	parts = [account_name.strip(), company.abbr]
	if cstr(account_number).strip():
		parts.insert(0, cstr(account_number).strip())
	return " - ".join(parts)


@frappe.whitelist()
def update_account_number(name, account_name, account_number=None, from_descendant=False):
	_ensure_idle_system()
	account = frappe.get_cached_doc("Account", name)
	if not account:
		return

	old_acc_name, old_acc_number = account.account_name, account.account_number

	# check if account exists in parent company
	ancestors = get_ancestors_of("Company", account.company)
	allow_independent_account_creation = frappe.get_cached_value(
		"Company", account.company, "allow_account_creation_against_child_company"
	)

	if ancestors and not allow_independent_account_creation:
		for ancestor in ancestors:
			old_name = frappe.db.get_value(
				"Account",
				{"account_number": old_acc_number, "account_name": old_acc_name, "company": ancestor},
				"name",
			)

			if old_name and not from_descendant:
				# same account in parent company exists
				allow_child_account_creation = _("Allow Account Creation Against Child Company")

				message = _("Account {0} exists in parent company {1}.").format(
					frappe.bold(old_acc_name), frappe.bold(ancestor)
				)
				message += "<br>"
				message += _("Renaming it is only allowed via parent company {0}, to avoid mismatch.").format(
					frappe.bold(ancestor)
				)
				message += "<br><br>"
				message += _("To overrule this, enable '{0}' in company {1}").format(
					allow_child_account_creation, frappe.bold(account.company)
				)

				frappe.throw(message, title=_("Rename Not Allowed"))

	account.validate_account_number(account_number)
	if account_number:
		frappe.db.set_value("Account", name, "account_number", account_number.strip())
	else:
		frappe.db.set_value("Account", name, "account_number", "")
	frappe.db.set_value("Account", name, "account_name", account_name.strip())

	if not from_descendant:
		# Update and rename in child company accounts as well
		descendants = get_descendants_of("Company", account.company)
		if descendants:
			sync_update_account_number_in_child(
				descendants, old_acc_name, account_name, account_number, old_acc_number
			)

	new_name = get_account_autoname(account_number, account_name, account.company)
	if name != new_name:
		frappe.rename_doc("Account", name, new_name, force=1)
		return new_name


@frappe.whitelist()
def merge_account(old, new):
	_ensure_idle_system()
	# Validate properties before merging
	new_account = frappe.get_cached_doc("Account", new)
	old_account = frappe.get_cached_doc("Account", old)

	if not new_account:
		throw(_("Account {0} does not exist").format(new))

	if (
		cint(new_account.is_group),
		new_account.root_type,
		new_account.company,
		cstr(new_account.account_currency),
	) != (
		cint(old_account.is_group),
		old_account.root_type,
		old_account.company,
		cstr(old_account.account_currency),
	):
		throw(
			msg=_(
				"""Merging is only possible if following properties are same in both records. Is Group, Root Type, Company and Account Currency"""
			),
			title=("Invalid Accounts"),
			exc=InvalidAccountMergeError,
		)

	if old_account.is_group and new_account.parent_account == old:
		new_account.db_set("parent_account", frappe.get_cached_value("Account", old, "parent_account"))

	frappe.rename_doc("Account", old, new, merge=1, force=1)

	return new


@frappe.whitelist()
def get_root_company(company):
	# return the topmost company in the hierarchy
	ancestors = get_ancestors_of("Company", company, "lft asc")
	return [ancestors[0]] if ancestors else []


def sync_update_account_number_in_child(
	descendants, old_acc_name, account_name, account_number=None, old_acc_number=None
):
	filters = {
		"company": ["in", descendants],
		"account_name": old_acc_name,
	}
	if old_acc_number:
		filters["account_number"] = old_acc_number

	for d in frappe.db.get_values("Account", filters=filters, fieldname=["company", "name"], as_dict=True):
		update_account_number(d["name"], account_name, account_number, from_descendant=True)


def _ensure_idle_system():
	# Don't allow renaming if accounting entries are actively being updated, there are two main reasons:
	# 1. Correctness: It's next to impossible to ensure that renamed account is not being used *right now*.
	# 2. Performance: Renaming requires locking out many tables entirely and severely degrades performance.

	if frappe.in_test:
		return

	last_gl_update = None
	try:
		# We also lock inserts to GL entry table with for_update here.
		last_gl_update = frappe.db.get_value("GL Entry", {}, "modified", for_update=True, wait=False)
	except frappe.QueryTimeoutError:
		# wait=False fails immediately if there's an active transaction.
		last_gl_update = add_to_date(None, seconds=-1)

	if not last_gl_update:
		return

	if last_gl_update > add_to_date(None, minutes=-5):
		frappe.throw(
			_(
				"Last GL Entry update was done {}. This operation is not allowed while system is actively being used. Please wait for 5 minutes before retrying."
			).format(pretty_date(last_gl_update)),
			title=_("System In Use"),
		)


def get_company_default_account_fields():
	return {
		"default_bank_account": "Default Bank Account",
		"default_cash_account": "Default Cash Account",
		"default_receivable_account": "Default Receivable Account",
		"default_payable_account": "Default Payable Account",
		"default_expense_account": "Default Expense Account",
		"default_income_account": "Default Income Account",
		"stock_received_but_not_billed": "Stock Received But Not Billed Account",
		"stock_adjustment_account": "Stock Adjustment Account",
		"write_off_account": "Write Off Account",
		"default_discount_account": "Default Payment Discount Account",
		"unrealized_profit_loss_account": "Unrealized Profit / Loss Account",
		"exchange_gain_loss_account": "Exchange Gain / Loss Account",
		"unrealized_exchange_gain_loss_account": "Unrealized Exchange Gain / Loss Account",
		"round_off_account": "Round Off Account",
		"default_deferred_revenue_account": "Default Deferred Revenue Account",
		"default_deferred_expense_account": "Default Deferred Expense Account",
		"accumulated_depreciation_account": "Accumulated Depreciation Account",
		"depreciation_expense_account": "Depreciation Expense Account",
		"disposal_account": "Gain/Loss Account on Asset Disposal",
	}
