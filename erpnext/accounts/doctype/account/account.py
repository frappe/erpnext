# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, fmt_money, cstr, cint
from frappe import msgprint, throw, _

get_value = frappe.db.get_value

from frappe.model.document import Document

class Account(Document):
	nsm_parent_field = 'parent_account'

	def autoname(self):
		self.doc.name = self.doc.account_name.strip() + ' - ' + \
			frappe.db.get_value("Company", self.doc.company, "abbr")

	def get_address(self):
		return {
			'address': frappe.db.get_value(self.doc.master_type, 
				self.doc.master_name, "address")
		}
		
	def validate(self): 
		self.validate_master_name()
		self.validate_parent()
		self.validate_duplicate_account()
		self.validate_root_details()
		self.validate_mandatory()
		self.validate_warehouse_account()
		self.validate_frozen_accounts_modifier()
	
		if not self.doc.parent_account:
			self.doc.parent_account = ''
		
	def validate_master_name(self):
		"""Remind to add master name"""
		if self.doc.master_type in ('Customer', 'Supplier') or self.doc.account_type == "Warehouse":
			if not self.doc.master_name:
				msgprint(_("Please enter Master Name once the account is created."))
			elif not frappe.db.exists(self.doc.master_type or self.doc.account_type, 
					self.doc.master_name):
				throw(_("Invalid Master Name"))
			
	def validate_parent(self):
		"""Fetch Parent Details and validation for account not to be created under ledger"""
		if self.doc.parent_account:
			par = frappe.db.sql("""select name, group_or_ledger, report_type 
				from tabAccount where name =%s""", self.doc.parent_account, as_dict=1)
			if not par:
				throw(_("Parent account does not exists"))
			elif par[0]["name"] == self.doc.name:
				throw(_("You can not assign itself as parent account"))
			elif par[0]["group_or_ledger"] != 'Group':
				throw(_("Parent account can not be a ledger"))
				
			if par[0]["report_type"]:
				self.doc.report_type = par[0]["report_type"]
	
	def validate_duplicate_account(self):
		if self.doc.fields.get('__islocal') or not self.doc.name:
			company_abbr = frappe.db.get_value("Company", self.doc.company, "abbr")
			if frappe.db.sql("""select name from tabAccount where name=%s""", 
				(self.doc.account_name + " - " + company_abbr)):
					throw("{name}: {acc_name} {exist}, {rename}".format(**{
						"name": _("Account Name"),
						"acc_name": self.doc.account_name,
						"exist": _("already exists"),
						"rename": _("please rename")
					}))
				
	def validate_root_details(self):
		#does not exists parent
		if frappe.db.exists("Account", self.doc.name):
			if not frappe.db.get_value("Account", self.doc.name, "parent_account"):
				throw(_("Root cannot be edited."))
				
	def validate_frozen_accounts_modifier(self):
		old_value = frappe.db.get_value("Account", self.doc.name, "freeze_account")
		if old_value and old_value != self.doc.freeze_account:
			frozen_accounts_modifier = frappe.db.get_value( 'Accounts Settings', None, 
				'frozen_accounts_modifier')
			if not frozen_accounts_modifier or \
				frozen_accounts_modifier not in frappe.user.get_roles():
					throw(_("You are not authorized to set Frozen value"))
			
	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			throw("{acc}: {account_name} {child}. {msg}".format(**{
				"acc": _("Account"),
				"account_name": self.doc.name,
				"child": _("has existing child"),
				"msg": _("You can not convert this account to ledger")
			}))
		elif self.check_gle_exists():
			throw(_("Account with existing transaction can not be converted to ledger."))
		else:
			self.doc.group_or_ledger = 'Ledger'
			self.doc.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			throw(_("Account with existing transaction can not be converted to group."))
		elif self.doc.master_type or self.doc.account_type:
			throw(_("Cannot covert to Group because Master Type or Account Type is selected."))
		else:
			self.doc.group_or_ledger = 'Group'
			self.doc.save()
			return 1

	# Check if any previous balance exists
	def check_gle_exists(self):
		return frappe.db.get_value("GL Entry", {"account": self.doc.name})

	def check_if_child_exists(self):
		return frappe.db.sql("""select name from `tabAccount` where parent_account = %s 
			and docstatus != 2""", self.doc.name)
	
	def validate_mandatory(self):
		if not self.doc.report_type:
			throw(_("Report Type is mandatory"))
			
	def validate_warehouse_account(self):
		if not cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
			return
			
		if self.doc.account_type == "Warehouse":
			old_warehouse = cstr(frappe.db.get_value("Account", self.doc.name, "master_name"))
			if old_warehouse != cstr(self.doc.master_name):
				if old_warehouse:
					self.validate_warehouse(old_warehouse)
				if self.doc.master_name:
					self.validate_warehouse(self.doc.master_name)
				else:
					throw(_("Master Name is mandatory if account type is Warehouse"))
		
	def validate_warehouse(self, warehouse):
		if frappe.db.get_value("Stock Ledger Entry", {"warehouse": warehouse}):
			throw(_("Stock transactions exist against warehouse ") + warehouse + 
				_(" .You can not assign / modify / remove Master Name"))

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
			where t2.name=%s and t1.name = t2.master_name""", self.doc.name)
		credit_limit = cr_limit and flt(cr_limit[0][0]) or 0
		if not credit_limit:
			credit_limit = frappe.db.get_value('Company', self.doc.company, 'credit_limit')
			credit_limit_from = 'Company'
		
		# If outstanding greater than credit limit and not authorized person raise exception
		if credit_limit > 0 and flt(total_outstanding) > credit_limit \
				and not self.get_authorized_user():
			throw("""Total Outstanding amount (%s) for <b>%s</b> can not be \
				greater than credit limit (%s). To change your credit limit settings, \
				please update in the <b>%s</b> master""" % (fmt_money(total_outstanding), 
				self.doc.name, fmt_money(credit_limit), credit_limit_from))
			
	def validate_trash(self):
		"""checks gl entries and if child exists"""
		if not self.doc.parent_account:
			throw(_("Root account can not be deleted"))
			
		if self.check_gle_exists():
			throw("""Account with existing transaction (Sales Invoice / Purchase Invoice / \
				Journal Voucher) can not be deleted""")
		if self.check_if_child_exists():
			throw(_("Child account exists for this account. You can not delete this account."))

	def on_trash(self): 
		self.validate_trash()
		self.update_nsm_model()
		
	def before_rename(self, old, new, merge=False):
		# Add company abbr if not provided
		from erpnext.setup.doctype.company.company import get_name_with_abbr
		new_account = get_name_with_abbr(new, self.doc.company)
		
		# Validate properties before merging
		if merge:
			if not frappe.db.exists("Account", new):
				throw(_("Account ") + new +_(" does not exists"))
				
			val = list(frappe.db.get_value("Account", new_account, 
				["group_or_ledger", "report_type", "company"]))
			
			if val != [self.doc.group_or_ledger, self.doc.report_type, self.doc.company]:
				throw(_("""Merging is only possible if following \
					properties are same in both records.
					Group or Ledger, Report Type, Company"""))
					
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