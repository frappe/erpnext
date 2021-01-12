# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, cstr
from frappe import throw, _
from frappe.utils.nestedset import NestedSet, get_ancestors_of, get_descendants_of

class RootNotEditable(frappe.ValidationError): pass
class BalanceMismatchError(frappe.ValidationError): pass

class Account(NestedSet):
	nsm_parent_field = 'parent_account'
	def on_update(self):
		if frappe.local.flags.ignore_on_update:
			return
		else:
			super(Account, self).on_update()

	def onload(self):
		frozen_accounts_modifier = frappe.db.get_value("Accounts Settings", "Accounts Settings",
			"frozen_accounts_modifier")
		if not frozen_accounts_modifier or frozen_accounts_modifier in frappe.get_roles():
			self.set_onload("can_freeze_account", True)

	def autoname(self):
		from erpnext.accounts.utils import get_autoname_with_number
		self.name = get_autoname_with_number(self.account_number, self.account_name, None, self.company)

	def validate(self):
		from erpnext.accounts.utils import validate_field_number
		if frappe.local.flags.allow_unverified_charts:
			return
		self.validate_parent()
		self.validate_root_details()
		validate_field_number("Account", self.name, self.account_number, self.company, "account_number")
		self.validate_group_or_ledger()
		self.set_root_and_report_type()
		self.validate_mandatory()
		self.validate_frozen_accounts_modifier()
		self.validate_balance_must_be_debit_or_credit()
		self.validate_account_currency()
		self.validate_root_company_and_sync_account_to_children()

	def validate_parent(self):
		"""Fetch Parent Details and validate parent account"""
		if self.parent_account:
			par = frappe.db.get_value("Account", self.parent_account,
				["name", "is_group", "company"], as_dict=1)
			if not par:
				throw(_("Account {0}: Parent account {1} does not exist").format(self.name, self.parent_account))
			elif par.name == self.name:
				throw(_("Account {0}: You can not assign itself as parent account").format(self.name))
			elif not par.is_group:
				throw(_("Account {0}: Parent account {1} can not be a ledger").format(self.name, self.parent_account))
			elif par.company != self.company:
				throw(_("Account {0}: Parent account {1} does not belong to company: {2}")
					.format(self.name, self.parent_account, self.company))

	def set_root_and_report_type(self):
		if self.parent_account:
			par = frappe.db.get_value("Account", self.parent_account,
				["report_type", "root_type"], as_dict=1)

			if par.report_type:
				self.report_type = par.report_type
			if par.root_type:
				self.root_type = par.root_type

		if self.is_group:
			db_value = frappe.db.get_value("Account", self.name, ["report_type", "root_type"], as_dict=1)
			if db_value:
				if self.report_type != db_value.report_type:
					frappe.db.sql("update `tabAccount` set report_type=%s where lft > %s and rgt < %s",
						(self.report_type, self.lft, self.rgt))
				if self.root_type != db_value.root_type:
					frappe.db.sql("update `tabAccount` set root_type=%s where lft > %s and rgt < %s",
						(self.root_type, self.lft, self.rgt))

		if self.root_type and not self.report_type:
			self.report_type = "Balance Sheet" \
				if self.root_type in ("Asset", "Liability", "Equity") else "Profit and Loss"

	def validate_root_details(self):
		# does not exists parent
		if frappe.db.exists("Account", self.name):
			if not frappe.db.get_value("Account", self.name, "parent_account"):
				throw(_("Root cannot be edited."), RootNotEditable)

		if not self.parent_account and not self.is_group:
			frappe.throw(_("The root account {0} must be a group").format(frappe.bold(self.name)))

	def validate_root_company_and_sync_account_to_children(self):
		# ignore validation while creating new compnay or while syncing to child companies
		if frappe.local.flags.ignore_root_company_validation or self.flags.ignore_root_company_validation:
			return
		ancestors = get_root_company(self.company)
		if ancestors:
			if frappe.get_value("Company", self.company, "allow_account_creation_against_child_company"):
				return
			if not frappe.db.get_value("Account",
				{'account_name': self.account_name, 'company': ancestors[0]}, 'name'):
				frappe.throw(_("Please add the account to root level Company - {}").format(ancestors[0]))
		elif self.parent_account:
			descendants = get_descendants_of('Company', self.company)
			if not descendants: return
			parent_acc_name_map = {}
			parent_acc_name, parent_acc_number = frappe.db.get_value('Account', self.parent_account, \
				["account_name", "account_number"])
			filters = {
				"company": ["in", descendants],
				"account_name": parent_acc_name,
			}
			if parent_acc_number:
				filters["account_number"] = parent_acc_number

			for d in frappe.db.get_values('Account', filters=filters, fieldname=["company", "name"], as_dict=True):
				parent_acc_name_map[d["company"]] = d["name"]

			if not parent_acc_name_map: return

			self.create_account_for_child_company(parent_acc_name_map, descendants, parent_acc_name)

	def validate_group_or_ledger(self):
		if self.get("__islocal"):
			return

		existing_is_group = frappe.db.get_value("Account", self.name, "is_group")
		if cint(self.is_group) != cint(existing_is_group):
			if self.check_gle_exists():
				throw(_("Account with existing transaction cannot be converted to ledger"))
			elif self.is_group:
				if self.account_type and not self.flags.exclude_account_type_check:
					throw(_("Cannot covert to Group because Account Type is selected."))
			elif self.check_if_child_exists():
				throw(_("Account with child nodes cannot be set as ledger"))

	def validate_frozen_accounts_modifier(self):
		old_value = frappe.db.get_value("Account", self.name, "freeze_account")
		if old_value and old_value != self.freeze_account:
			frozen_accounts_modifier = frappe.db.get_value('Accounts Settings', None, 'frozen_accounts_modifier')
			if not frozen_accounts_modifier or \
				frozen_accounts_modifier not in frappe.get_roles():
					throw(_("You are not authorized to set Frozen value"))

	def validate_balance_must_be_debit_or_credit(self):
		from erpnext.accounts.utils import get_balance_on
		if not self.get("__islocal") and self.balance_must_be:
			account_balance = get_balance_on(self.name)

			if account_balance > 0 and self.balance_must_be == "Credit":
				frappe.throw(_("Account balance already in Debit, you are not allowed to set 'Balance Must Be' as 'Credit'"))
			elif account_balance < 0 and self.balance_must_be == "Debit":
				frappe.throw(_("Account balance already in Credit, you are not allowed to set 'Balance Must Be' as 'Debit'"))

	def validate_account_currency(self):
		if not self.account_currency:
			self.account_currency = frappe.get_cached_value('Company',  self.company,  "default_currency")

		elif self.account_currency != frappe.db.get_value("Account", self.name, "account_currency"):
			if frappe.db.get_value("GL Entry", {"account": self.name}):
				frappe.throw(_("Currency can not be changed after making entries using some other currency"))

	def create_account_for_child_company(self, parent_acc_name_map, descendants, parent_acc_name):
		for company in descendants:
			company_bold = frappe.bold(company)
			parent_acc_name_bold = frappe.bold(parent_acc_name)
			if not parent_acc_name_map.get(company):
				frappe.throw(_("While creating account for Child Company {0}, parent account {1} not found. Please create the parent account in corresponding COA")
					.format(company_bold, parent_acc_name_bold), title=_("Account Not Found"))

			# validate if parent of child company account to be added is a group
			if (frappe.db.get_value("Account", self.parent_account, "is_group")
				and not frappe.db.get_value("Account", parent_acc_name_map[company], "is_group")):
				msg = _("While creating account for Child Company {0}, parent account {1} found as a ledger account.").format(company_bold, parent_acc_name_bold)
				msg += "<br><br>"
				msg += _("Please convert the parent account in corresponding child company to a group account.")
				frappe.throw(msg, title=_("Invalid Parent Account"))

			filters = {
				"account_name": self.account_name,
				"company": company
			}

			if self.account_number:
				filters["account_number"] = self.account_number

			child_account = frappe.db.get_value("Account", filters, 'name')
			if not child_account:
				doc = frappe.copy_doc(self)
				doc.flags.ignore_root_company_validation = True
				doc.update({
					"company": company,
					# parent account's currency should be passed down to child account's curreny
					# if it is None, it picks it up from default company currency, which might be unintended
					"account_currency": self.account_currency,
					"parent_account": parent_acc_name_map[company]
				})

				doc.save()
				frappe.msgprint(_("Account {0} is added in the child company {1}")
					.format(doc.name, company))
			elif child_account:
				# update the parent company's value in child companies
				doc = frappe.get_doc("Account", child_account)
				parent_value_changed = False
				for field in ['account_type', 'account_currency',
					'freeze_account', 'balance_must_be']:
					if doc.get(field) != self.get(field):
						parent_value_changed = True
						doc.set(field, self.get(field))

				if parent_value_changed:
					doc.save()

	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			throw(_("Account with child nodes cannot be converted to ledger"))
		elif self.check_gle_exists():
			throw(_("Account with existing transaction cannot be converted to ledger"))
		else:
			self.is_group = 0
			self.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be converted to group."))
		elif self.account_type and not self.flags.exclude_account_type_check:
			throw(_("Cannot covert to Group because Account Type is selected."))
		else:
			self.is_group = 1
			self.save()
			return 1

	# Check if any previous balance exists
	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"account": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql("""select name from `tabAccount` where parent_account = %s
			and docstatus != 2""", self.name)

	def validate_mandatory(self):
		if not self.root_type:
			throw(_("Root Type is mandatory"))

		if not self.report_type:
			throw(_("Report Type is mandatory"))

	def on_trash(self):
		# checks gl entries and if child exists
		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be deleted"))

		super(Account, self).on_trash(True)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_parent_account(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name from tabAccount
		where is_group = 1 and docstatus != 2 and company = %s
		and %s like %s order by name limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"),
		(filters["company"], "%%%s%%" % txt, start, page_len), as_list=1)

def get_account_currency(account):
	"""Helper function to get account currency"""
	if not account:
		return
	def generator():
		account_currency, company = frappe.get_cached_value("Account", account, ["account_currency", "company"])
		if not account_currency:
			account_currency = frappe.get_cached_value('Company',  company,  "default_currency")

		return account_currency

	return frappe.local_cache("account_currency", account, generator)

def on_doctype_update():
	frappe.db.add_index("Account", ["lft", "rgt"])

def get_account_autoname(account_number, account_name, company):
	# first validate if company exists
	company = frappe.get_cached_value('Company',  company,  ["abbr", "name"], as_dict=True)
	if not company:
		frappe.throw(_('Company {0} does not exist').format(company))

	parts = [account_name.strip(), company.abbr]
	if cstr(account_number).strip():
		parts.insert(0, cstr(account_number).strip())
	return ' - '.join(parts)

def validate_account_number(name, account_number, company):
	if account_number:
		account_with_same_number = frappe.db.get_value("Account",
			{"account_number": account_number, "company": company, "name": ["!=", name]})
		if account_with_same_number:
			frappe.throw(_("Account Number {0} already used in account {1}")
				.format(account_number, account_with_same_number))

@frappe.whitelist()
def update_account_number(name, account_name, account_number=None, from_descendant=False):
	account = frappe.db.get_value("Account", name, "company", as_dict=True)
	if not account: return

	old_acc_name, old_acc_number = frappe.db.get_value('Account', name, \
				["account_name", "account_number"])

	# check if account exists in parent company
	ancestors = get_ancestors_of("Company", account.company)
	allow_independent_account_creation = frappe.get_value("Company", account.company, "allow_account_creation_against_child_company")

	if ancestors and not allow_independent_account_creation:
		for ancestor in ancestors:
			if frappe.db.get_value("Account", {'account_name': old_acc_name, 'company': ancestor}, 'name'):
				# same account in parent company exists
				allow_child_account_creation = _("Allow Account Creation Against Child Company")

				message = _("Account {0} exists in parent company {1}.").format(frappe.bold(old_acc_name), frappe.bold(ancestor))
				message += "<br>"
				message += _("Renaming it is only allowed via parent company {0}, to avoid mismatch.").format(frappe.bold(ancestor))
				message += "<br><br>"
				message += _("To overrule this, enable '{0}' in company {1}").format(allow_child_account_creation, frappe.bold(account.company))

				frappe.throw(message, title=_("Rename Not Allowed"))

	validate_account_number(name, account_number, account.company)
	if account_number:
		frappe.db.set_value("Account", name, "account_number", account_number.strip())
	else:
		frappe.db.set_value("Account", name, "account_number", "")
	frappe.db.set_value("Account", name, "account_name", account_name.strip())

	if not from_descendant:
		# Update and rename in child company accounts as well
		descendants = get_descendants_of('Company', account.company)
		if descendants:
			sync_update_account_number_in_child(descendants, old_acc_name, account_name, account_number, old_acc_number)

	new_name = get_account_autoname(account_number, account_name, account.company)
	if name != new_name:
		frappe.rename_doc("Account", name, new_name, force=1)
		return new_name

@frappe.whitelist()
def merge_account(old, new, is_group, root_type, company):
	# Validate properties before merging
	if not frappe.db.exists("Account", new):
		throw(_("Account {0} does not exist").format(new))

	val = list(frappe.db.get_value("Account", new,
		["is_group", "root_type", "company"]))

	if val != [cint(is_group), root_type, company]:
		throw(_("""Merging is only possible if following properties are same in both records. Is Group, Root Type, Company"""))

	if is_group and frappe.db.get_value("Account", new, "parent_account") == old:
		frappe.db.set_value("Account", new, "parent_account",
			frappe.db.get_value("Account", old, "parent_account"))

	frappe.rename_doc("Account", old, new, merge=1, force=1)

	return new

@frappe.whitelist()
def get_root_company(company):
	# return the topmost company in the hierarchy
	ancestors = get_ancestors_of('Company', company, "lft asc")
	return [ancestors[0]] if ancestors else []

def sync_update_account_number_in_child(descendants, old_acc_name, account_name, account_number=None, old_acc_number=None):
	filters = {
		"company": ["in", descendants],
		"account_name": old_acc_name,
	}
	if old_acc_number:
		filters["account_number"] = old_acc_number

	for d in frappe.db.get_values('Account', filters=filters, fieldname=["company", "name"], as_dict=True):
			update_account_number(d["name"], account_name, account_number, from_descendant=True)
