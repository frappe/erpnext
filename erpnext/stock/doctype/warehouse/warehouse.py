# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import cint, validate_email_add
from frappe import throw, msgprint, _
from frappe.utils.nestedset import NestedSet

class Warehouse(NestedSet):
	nsm_parent_field = 'parent_warehouse'

	def autoname(self):
		if self.company:
			suffix = " - " + frappe.db.get_value("Company", self.company, "abbr")
			if not self.warehouse_name.endswith(suffix):
				self.name = self.warehouse_name + suffix
		else:
			self.name = self.warehouse_name

	def onload(self):
		'''load account name for General Ledger Report'''
		account = frappe.db.get_value("Account", {
			"account_type": "Stock", "company": self.company, "warehouse": self.name, "is_group": 0})

		if account:
			self.set_onload('account', account)

	def validate(self):
		if self.email_id:
			validate_email_add(self.email_id, True)

		self.update_parent_account()

	def update_parent_account(self):
		if not getattr(self, "__islocal", None) \
			and cint(frappe.defaults.get_global_default("auto_accounting_for_stock")) \
			and (self.create_account_under != frappe.db.get_value("Warehouse", self.name, "create_account_under")):

				self.validate_parent_account()

				warehouse_account = frappe.db.get_value("Account",
					{"account_type": "Stock", "company": self.company, "warehouse": self.name, "is_group": 0},
					["name", "parent_account"])

				if warehouse_account and warehouse_account[1] != self.create_account_under:
					acc_doc = frappe.get_doc("Account", warehouse_account[0])
					acc_doc.parent_account = self.create_account_under
					acc_doc.save()

	def on_update(self):
		self.create_account_head()
		self.update_nsm_model()

	def create_account_head(self):
		'''Create new account head if there is no account linked to this Warehouse'''
		from erpnext.accounts.doctype.account.account import BalanceMismatchError
		if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
			if not self.get_account():
				if self.get("__islocal") or not frappe.db.get_value(
						"Stock Ledger Entry", {"warehouse": self.name}):

					self.validate_parent_account()
					ac_doc = frappe.get_doc({
						"doctype": "Account",
						'account_name': self.warehouse_name,
						'parent_account': self.parent_warehouse if self.parent_warehouse \
							else self.create_account_under,
						'is_group': self.is_group,
						'company':self.company,
						"account_type": "Stock",
						"warehouse": self.name,
						"freeze_account": "No"
					})
					ac_doc.flags.ignore_permissions = True
					ac_doc.flags.ignore_mandatory = True
					try:
						ac_doc.insert()
						msgprint(_("Account head {0} created").format(ac_doc.name), indicator='green', alert=True)

					except frappe.DuplicateEntryError:
						msgprint(_("Please create an Account for this Warehouse and link it. This cannot be done automatically as an account with name {0} already exists").format(frappe.bold(self.name)),
							indicator='orange')

					except BalanceMismatchError:
						msgprint(_("Cannot automatically create Account as there is already stock balance in the Account. You must create a matching account before you can make an entry on this warehouse"))

	def validate_parent_account(self):
		if not self.company:
			frappe.throw(_("Warehouse {0}: Company is mandatory").format(self.name))

		if not self.create_account_under:
			parent_account = frappe.db.sql("""select name from tabAccount
				where account_type='Stock' and company=%s and is_group=1
				and (warehouse is null or warehouse = '')""", self.company)

			if parent_account:
				frappe.db.set_value("Warehouse", self.name, "create_account_under", parent_account[0][0])
				self.create_account_under = parent_account[0][0]
		elif frappe.db.get_value("Account", self.create_account_under, "company") != self.company:
			frappe.throw(_("Warehouse {0}: Parent account {1} does not bolong to the company {2}")
				.format(self.name, self.create_account_under, self.company))

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_trash(self):
		# delete bin
		bins = frappe.db.sql("select * from `tabBin` where warehouse = %s",
			self.name, as_dict=1)
		for d in bins:
			if d['actual_qty'] or d['reserved_qty'] or d['ordered_qty'] or \
					d['indented_qty'] or d['projected_qty'] or d['planned_qty']:
				throw(_("Warehouse {0} can not be deleted as quantity exists for Item {1}").format(self.name, d['item_code']))
			else:
				frappe.db.sql("delete from `tabBin` where name = %s", d['name'])

		warehouse_account = self.get_account()
		if warehouse_account:
			frappe.delete_doc("Account", warehouse_account)

		if self.check_if_sle_exists():
			throw(_("Warehouse can not be deleted as stock ledger entry exists for this warehouse."))

		if self.check_if_child_exists():
			throw(_("Child warehouse exists for this warehouse. You can not delete this warehouse."))

		self.update_nsm_model()

	def check_if_sle_exists(self):
		return frappe.db.sql("""select name from `tabStock Ledger Entry`
			where warehouse = %s""", self.name)

	def check_if_child_exists(self):
		return frappe.db.sql("""select name from `tabWarehouse`
			where parent_warehouse = %s""", self.name)

	def before_rename(self, old_name, new_name, merge=False):
		# Add company abbr if not provided
		new_warehouse = erpnext.encode_company_abbr(new_name, self.company)

		if merge:
			if not frappe.db.exists("Warehouse", new_warehouse):
				frappe.throw(_("Warehouse {0} does not exist").format(new_warehouse))

			if self.company != frappe.db.get_value("Warehouse", new_warehouse, "company"):
				frappe.throw(_("Both Warehouse must belong to same Company"))

		self.rename_account_for(old_name, new_warehouse, merge)

		return new_warehouse

	def rename_account_for(self, old_name, new_name, merge):
		old_account_name = frappe.get_value('Account', dict(warehouse=old_name))

		if old_account_name:
			if not merge:
				# old account name is same as old name, so rename the account too
				if old_account_name == erpnext.encode_company_abbr(old_name, self.company):
					frappe.rename_doc("Account", old_account_name, new_name)
			else:
				# merge
				target_account = frappe.get_value('Account', dict(warehouse=new_name))
				if target_account:
					# target warehouse has account, merge into target account
					frappe.rename_doc("Account", old_account_name,
						target_account, merge=True)
				else:
					# target warehouse does not have account, use this account
					frappe.rename_doc("Account", old_account_name,
						new_name, merge=False)

					# rename link
					frappe.db.set_value('Account', new_name, 'warehouse', new_name)

	def get_account(self):
		return frappe.get_value('Account', dict(warehouse=self.name))

	def after_rename(self, old_name, new_name, merge=False):
		new_warehouse_name = self.get_new_warehouse_name_without_abbr(new_name)
		self.db_set("warehouse_name", new_warehouse_name)
				
		if merge:
			self.recalculate_bin_qty(new_name)
			
	def get_new_warehouse_name_without_abbr(self, name):
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		parts = name.rsplit(" - ", 1)
		
		if parts[-1].lower() == company_abbr.lower():
			name = parts[0]
			
		return name

	def recalculate_bin_qty(self, new_name):
		from erpnext.stock.stock_balance import repost_stock
		frappe.db.auto_commit_on_many_writes = 1
		existing_allow_negative_stock = frappe.db.get_value("Stock Settings", None, "allow_negative_stock")
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

		repost_stock_for_items = frappe.db.sql_list("""select distinct item_code
			from tabBin where warehouse=%s""", new_name)

		# Delete all existing bins to avoid duplicate bins for the same item and warehouse
		frappe.db.sql("delete from `tabBin` where warehouse=%s", new_name)

		for item_code in repost_stock_for_items:
			repost_stock(item_code, new_name)

		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", existing_allow_negative_stock)
		frappe.db.auto_commit_on_many_writes = 0

	def convert_to_group_or_ledger(self):
		if self.is_group:
			self.convert_to_ledger()
		else:
			self.convert_to_group()

	def convert_to_ledger(self):
		if self.check_if_child_exists():
			frappe.throw(_("Warehouses with child nodes cannot be converted to ledger"))
		elif self.check_if_sle_exists():
			throw(_("Warehouses with existing transaction can not be converted to ledger."))
		else:
			account_name = self.get_account()
			if account_name:
				doc = frappe.get_doc("Account", account_name)
				doc.warehouse = self.name
				doc.convert_group_to_ledger()

			self.is_group = 0
			self.save()
			return 1

	def convert_to_group(self):
		if self.check_if_sle_exists():
			throw(_("Warehouses with existing transaction can not be converted to group."))
		else:
			account_name = self.get_account()
			if account_name:
				doc = frappe.get_doc("Account", account_name)
				doc.flags.exclude_account_type_check = True
				doc.convert_ledger_to_group()

			self.is_group = 1
			self.save()
			return 1

@frappe.whitelist()
def get_children():
	from erpnext.stock.utils import get_stock_value_on
	doctype = frappe.local.form_dict.get('doctype')
	company = frappe.local.form_dict.get('company')

	parent_field = 'parent_' + doctype.lower().replace(' ', '_')
	parent = frappe.form_dict.get("parent") or ""

	if parent == "Warehouses":
		parent = ""

	warehouses = frappe.db.sql("""select name as value,
		is_group as expandable
		from `tab{doctype}`
		where docstatus < 2
		and ifnull(`{parent_field}`,'') = %s
		and (`company` = %s or company is null or company = '')
		order by name""".format(doctype=frappe.db.escape(doctype),
		parent_field=frappe.db.escape(parent_field)), (parent, company), as_dict=1)

	# return warehouses
	for wh in warehouses:
		wh["balance"] = get_stock_value_on(warehouse=wh.value)
	return warehouses

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = make_tree_args(**frappe.form_dict)

	if cint(args.is_root):
		args.parent_warehouse = None

	frappe.get_doc(args).insert()

@frappe.whitelist()
def convert_to_group_or_ledger():
	args = frappe.form_dict
	return frappe.get_doc("Warehouse", args.docname).convert_to_group_or_ledger()
