# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import defaultdict

import frappe
from frappe import _, throw
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import cint, flt
from frappe.utils.nestedset import NestedSet
from pypika.terms import ExistsCriterion

from erpnext.stock import get_warehouse_account


class Warehouse(NestedSet):
	nsm_parent_field = "parent_warehouse"

	def autoname(self):
		if self.company:
			suffix = " - " + frappe.get_cached_value("Company", self.company, "abbr")
			if not self.warehouse_name.endswith(suffix):
				self.name = self.warehouse_name + suffix
				return

		self.name = self.warehouse_name

	def onload(self):
		"""load account name for General Ledger Report"""
		if self.company and cint(
			frappe.db.get_value("Company", self.company, "enable_perpetual_inventory")
		):
			account = self.account or get_warehouse_account(self)

			if account:
				self.set_onload("account", account)
		load_address_and_contact(self)

	def validate(self):
		self.warn_about_multiple_warehouse_account()

	def on_update(self):
		self.update_nsm_model()

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_trash(self):
		# delete bin
		bins = frappe.get_all("Bin", fields="*", filters={"warehouse": self.name})
		for d in bins:
			if (
				d["actual_qty"]
				or d["reserved_qty"]
				or d["ordered_qty"]
				or d["indented_qty"]
				or d["projected_qty"]
				or d["planned_qty"]
			):
				throw(
					_("Warehouse {0} can not be deleted as quantity exists for Item {1}").format(
						self.name, d["item_code"]
					)
				)

		if self.check_if_sle_exists():
			throw(_("Warehouse can not be deleted as stock ledger entry exists for this warehouse."))

		if self.check_if_child_exists():
			throw(_("Child warehouse exists for this warehouse. You can not delete this warehouse."))

		frappe.db.delete("Bin", filters={"warehouse": self.name})
		self.update_nsm_model()
		self.unlink_from_items()

	def warn_about_multiple_warehouse_account(self):
		"If Warehouse value is split across multiple accounts, warn."

		def get_accounts_where_value_is_booked(name):
			sle = frappe.qb.DocType("Stock Ledger Entry")
			gle = frappe.qb.DocType("GL Entry")
			ac = frappe.qb.DocType("Account")

			return (
				frappe.qb.from_(sle)
				.join(gle)
				.on(sle.voucher_no == gle.voucher_no)
				.join(ac)
				.on(ac.name == gle.account)
				.select(gle.account)
				.distinct()
				.where((sle.warehouse == name) & (ac.account_type == "Stock"))
				.orderby(sle.creation)
				.run(as_dict=True)
			)

		if self.is_new():
			return

		old_wh_account = frappe.db.get_value("Warehouse", self.name, "account")

		# WH account is being changed or set get all accounts against which wh value is booked
		if self.account != old_wh_account:
			accounts = get_accounts_where_value_is_booked(self.name)
			accounts = [d.account for d in accounts]

			if not accounts or (len(accounts) == 1 and self.account in accounts):
				# if same singular account has stock value booked ignore
				return

			warning = _("Warehouse's Stock Value has already been booked in the following accounts:")
			account_str = "<br>" + ", ".join(frappe.bold(ac) for ac in accounts)
			reason = "<br><br>" + _(
				"Booking stock value across multiple accounts will make it harder to track stock and account value."
			)

			frappe.msgprint(
				warning + account_str + reason,
				title=_("Multiple Warehouse Accounts"),
				indicator="orange",
			)

	def check_if_sle_exists(self):
		return frappe.db.exists("Stock Ledger Entry", {"warehouse": self.name})

	def check_if_child_exists(self):
		return frappe.db.exists("Warehouse", {"parent_warehouse": self.name})

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
			self.is_group = 0
			self.save()
			return 1

	def convert_to_group(self):
		if self.check_if_sle_exists():
			throw(_("Warehouses with existing transaction can not be converted to group."))
		else:
			self.is_group = 1
			self.save()
			return 1

	def unlink_from_items(self):
		frappe.db.set_value("Item Default", {"default_warehouse": self.name}, "default_warehouse", None)


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	if is_root:
		parent = ""

	fields = ["name as value", "is_group as expandable"]
	filters = [
		["ifnull(`parent_warehouse`, '')", "=", parent],
		["company", "in", (company, None, "")],
	]

	warehouses = frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")

	company_currency = ""
	if company:
		company_currency = frappe.get_cached_value("Company", company, "default_currency")

	warehouse_wise_value = get_warehouse_wise_stock_value(company)

	# return warehouses
	for wh in warehouses:
		wh["balance"] = warehouse_wise_value.get(wh.value)
		if company_currency:
			wh["company_currency"] = company_currency
	return warehouses


def get_warehouse_wise_stock_value(company):
	warehouses = frappe.get_all(
		"Warehouse", fields=["name", "parent_warehouse"], filters={"company": company}
	)
	parent_warehouse = {d.name: d.parent_warehouse for d in warehouses}

	filters = {"warehouse": ("in", [data.name for data in warehouses])}
	bin_data = frappe.get_all(
		"Bin",
		fields=["sum(stock_value) as stock_value", "warehouse"],
		filters=filters,
		group_by="warehouse",
	)

	warehouse_wise_stock_value = defaultdict(float)
	for row in bin_data:
		if not row.stock_value:
			continue

		warehouse_wise_stock_value[row.warehouse] = row.stock_value
		update_value_in_parent_warehouse(
			warehouse_wise_stock_value, parent_warehouse, row.warehouse, row.stock_value
		)

	return warehouse_wise_stock_value


def update_value_in_parent_warehouse(
	warehouse_wise_stock_value, parent_warehouse_dict, warehouse, stock_value
):
	parent_warehouse = parent_warehouse_dict.get(warehouse)
	if not parent_warehouse:
		return

	warehouse_wise_stock_value[parent_warehouse] += flt(stock_value)
	update_value_in_parent_warehouse(
		warehouse_wise_stock_value, parent_warehouse_dict, parent_warehouse, stock_value
	)


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = make_tree_args(**frappe.form_dict)

	if cint(args.is_root):
		args.parent_warehouse = None

	frappe.get_doc(args).insert()


@frappe.whitelist()
def convert_to_group_or_ledger(docname=None):
	if not docname:
		docname = frappe.form_dict.docname
	return frappe.get_doc("Warehouse", docname).convert_to_group_or_ledger()


def get_child_warehouses(warehouse):
	from frappe.utils.nestedset import get_descendants_of

	children = get_descendants_of("Warehouse", warehouse, ignore_permissions=True, order_by="lft")
	return children + [warehouse]  # append self for backward compatibility


def get_warehouses_based_on_account(account, company=None):
	warehouses = []
	for d in frappe.get_all("Warehouse", fields=["name", "is_group"], filters={"account": account}):
		if d.is_group:
			warehouses.extend(get_child_warehouses(d.name))
		else:
			warehouses.append(d.name)

	if (
		not warehouses
		and company
		and frappe.get_cached_value("Company", company, "default_inventory_account") == account
	):
		warehouses = [d.name for d in frappe.get_all("Warehouse", filters={"is_group": 0})]

	if not warehouses:
		frappe.throw(_("Warehouse not found against the account {0}").format(account))

	return warehouses


# Will be use for frappe.qb
def apply_warehouse_filter(query, sle, filters):
	if warehouse := filters.get("warehouse"):
		warehouse_table = frappe.qb.DocType("Warehouse")

		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		chilren_subquery = (
			frappe.qb.from_(warehouse_table)
			.select(warehouse_table.name)
			.where(
				(warehouse_table.lft >= lft)
				& (warehouse_table.rgt <= rgt)
				& (warehouse_table.name == sle.warehouse)
			)
		)
		query = query.where(ExistsCriterion(chilren_subquery))

	return query
