# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr, cint, getdate, add_days, formatdate
from frappe import msgprint, throw, _
from frappe.model.document import Document

class Account(Document):
	nsm_parent_field = 'parent_account'

	def onload(self):
		frozen_accounts_modifier = frappe.db.get_value("Accounts Settings", "Accounts Settings",
			"frozen_accounts_modifier")
		if not frozen_accounts_modifier or frozen_accounts_modifier in frappe.user.get_roles():
			self.get("__onload").can_freeze_account = True

	def autoname(self):
		self.name = self.account_name.strip() + ' - ' + \
			frappe.db.get_value("Company", self.company, "abbr")

	def get_address(self):
		return {'address': frappe.db.get_value(self.master_type, self.master_name, "address")}

	def validate(self):
		self.validate_master_name()
		self.validate_parent()
		self.validate_root_details()
		self.validate_mandatory()
		self.validate_warehouse_account()
		self.validate_frozen_accounts_modifier()
		self.validate_balance_must_be_debit_or_credit()

	def validate_master_name(self):
		if self.master_type in ('Customer', 'Supplier') or self.account_type == "Warehouse":
			if not self.master_name:
				msgprint(_("Please enter Master Name once the account is created."))
			elif not frappe.db.exists(self.master_type or self.account_type, self.master_name):
				throw(_("Invalid Master Name"))

	def validate_parent(self):
		"""Fetch Parent Details and validate parent account"""
		if self.parent_account:
			par = frappe.db.get_value("Account", self.parent_account,
				["name", "group_or_ledger", "report_type", "root_type", "company"], as_dict=1)
			if not par:
				throw(_("Account {0}: Parent account {1} does not exist").format(self.name, self.parent_account))
			elif par.name == self.name:
				throw(_("Account {0}: You can not assign itself as parent account").format(self.name))
			elif par.group_or_ledger != 'Group':
				throw(_("Account {0}: Parent account {1} can not be a ledger").format(self.name, self.parent_account))
			elif par.company != self.company:
				throw(_("Account {0}: Parent account {1} does not belong to company: {2}")
					.format(self.name, self.parent_account, self.company))

			if par.report_type:
				self.report_type = par.report_type
			if par.root_type:
				self.root_type = par.root_type

	def validate_root_details(self):
		#does not exists parent
		if frappe.db.exists("Account", self.name):
			if not frappe.db.get_value("Account", self.name, "parent_account"):
				throw(_("Root cannot be edited."))

	def validate_frozen_accounts_modifier(self):
		old_value = frappe.db.get_value("Account", self.name, "freeze_account")
		if old_value and old_value != self.freeze_account:
			frozen_accounts_modifier = frappe.db.get_value('Accounts Settings', None, 'frozen_accounts_modifier')
			if not frozen_accounts_modifier or \
				frozen_accounts_modifier not in frappe.user.get_roles():
					throw(_("You are not authorized to set Frozen value"))

	def validate_balance_must_be_debit_or_credit(self):
		from erpnext.accounts.utils import get_balance_on
		if not self.get("__islocal") and self.balance_must_be:
			account_balance = get_balance_on(self.name)

			if account_balance > 0 and self.balance_must_be == "Credit":
				frappe.throw(_("Account balance already in Debit, you are not allowed to set 'Balance Must Be' as 'Credit'"))
			elif account_balance < 0 and self.balance_must_be == "Debit":
				frappe.throw(_("Account balance already in Credit, you are not allowed to set 'Balance Must Be' as 'Debit'"))

	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			throw(_("Account with child nodes cannot be converted to ledger"))
		elif self.check_gle_exists():
			throw(_("Account with existing transaction cannot be converted to ledger"))
		else:
			self.group_or_ledger = 'Ledger'
			self.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be converted to group."))
		elif self.master_type or self.account_type:
			throw(_("Cannot covert to Group because Master Type or Account Type is selected."))
		else:
			self.group_or_ledger = 'Group'
			self.save()
			return 1

	# Check if any previous balance exists
	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"account": self.name})

	def check_if_child_exists(self):
		return frappe.db.sql("""select name from `tabAccount` where parent_account = %s
			and docstatus != 2""", self.name)

	def validate_mandatory(self):
		if not self.report_type:
			throw(_("Report Type is mandatory"))

		if not self.root_type:
			throw(_("Root Type is mandatory"))

	def validate_warehouse_account(self):
		if not cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
			return

		if self.account_type == "Warehouse":
			old_warehouse = cstr(frappe.db.get_value("Account", self.name, "master_name"))
			if old_warehouse != cstr(self.master_name):
				if old_warehouse:
					self.validate_warehouse(old_warehouse)
				if self.master_name:
					self.validate_warehouse(self.master_name)
				else:
					throw(_("Master Name is mandatory if account type is Warehouse"))

	def validate_warehouse(self, warehouse):
		if frappe.db.get_value("Stock Ledger Entry", {"warehouse": warehouse}):
			throw(_("Stock entries exist against warehouse {0} cannot re-assign or modify 'Master Name'").format(warehouse))

	def update_nsm_model(self):
		"""update lft, rgt indices for nested set model"""
		import frappe
		import frappe.utils.nestedset
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()

	def get_authorized_user(self):
		# Check logged-in user is authorized
		if frappe.db.get_value('Accounts Settings', None, 'credit_controller') \
				in frappe.user.get_roles():
			return 1

	def check_credit_limit(self, total_outstanding):
		# Get credit limit
		credit_limit_from = 'Customer'

		cr_limit = frappe.db.sql("""select t1.credit_limit from tabCustomer t1, `tabAccount` t2
			where t2.name=%s and t1.name = t2.master_name""", self.name)
		credit_limit = cr_limit and flt(cr_limit[0][0]) or 0
		if not credit_limit:
			credit_limit = frappe.db.get_value('Company', self.company, 'credit_limit')
			credit_limit_from = 'Company'

		# If outstanding greater than credit limit and not authorized person raise exception
		if credit_limit > 0 and flt(total_outstanding) > credit_limit \
				and not self.get_authorized_user():
			throw(_("{0} Credit limit {1} crossed").format(_(credit_limit_from), credit_limit))

	def validate_due_date(self, posting_date, due_date):
		credit_days = (self.credit_days or frappe.db.get_value("Company", self.company, "credit_days"))
		if credit_days is None:
			return

		posting_date, due_date = getdate(posting_date), getdate(due_date)
		diff = (due_date - posting_date).days

		if diff < 0:
			frappe.throw(_("Due Date cannot be before Posting Date"))
		elif diff > credit_days:
			is_credit_controller = frappe.db.get_value("Accounts Settings", None,
				"credit_controller") in frappe.user.get_roles()

			if is_credit_controller:
				msgprint(_("Note: Due Date exceeds the allowed credit days by {0} day(s)").format(
					diff - credit_days))
			else:
				max_due_date = formatdate(add_days(posting_date, credit_days))
				frappe.throw(_("Due Date cannot be after {0}").format(max_due_date))

	def validate_trash(self):
		"""checks gl entries and if child exists"""
		if not self.parent_account:
			throw(_("Root account can not be deleted"))

		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be deleted"))
		if self.check_if_child_exists():
			throw(_("Child account exists for this account. You can not delete this account."))

	def on_trash(self):
		self.validate_trash()
		self.update_nsm_model()

	def before_rename(self, old, new, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr
		new_account = get_name_with_abbr(new, self.company)

		# Validate properties before merging
		if merge:
			if not frappe.db.exists("Account", new):
				throw(_("Account {0} does not exist").format(new))

			val = list(frappe.db.get_value("Account", new_account,
				["group_or_ledger", "root_type", "company"]))

			if val != [self.group_or_ledger, self.root_type, self.company]:
				throw(_("""Merging is only possible if following properties are same in both records. Group or Ledger, Root Type, Company"""))

		return new_account

	def after_rename(self, old, new, merge=False):
		if not merge:
			frappe.db.set_value("Account", new, "account_name",
				" - ".join(new.split(" - ")[:-1]))
		else:
			from frappe.utils.nestedset import rebuild_tree
			rebuild_tree("Account", "parent_account")

def get_master_name(doctype, txt, searchfield, start, page_len, filters):
	conditions = (" and company='%s'"% filters["company"].replace("'", "\'")) if doctype == "Warehouse" else ""

	return frappe.db.sql("""select name from `tab%s` where %s like %s %s
		order by name limit %s, %s""" %
		(filters["master_type"], searchfield, "%s", conditions, "%s", "%s"),
		("%%%s%%" % txt, start, page_len), as_list=1)

def get_parent_account(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name from tabAccount
		where group_or_ledger = 'Group' and docstatus != 2 and company = %s
		and %s like %s order by name limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"),
		(filters["company"], "%%%s%%" % txt, start, page_len), as_list=1)
