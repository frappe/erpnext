# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _, throw
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.query_builder import Field
from frappe.query_builder.functions import IfNull
from frappe.utils import cint
from frappe.utils.caching import request_cache
from frappe.utils.nestedset import NestedSet
from pypika.terms import ExistsCriterion

from erpnext.stock import get_warehouse_account


class Warehouse(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		address_line_1: DF.Data | None
		address_line_2: DF.Data | None
		city: DF.Data | None
		company: DF.Link
		customer: DF.Link | None
		default_in_transit_warehouse: DF.Link | None
		disabled: DF.Check
		email_id: DF.Data | None
		is_group: DF.Check
		is_rejected_warehouse: DF.Check
		lft: DF.Int
		mobile_no: DF.Data | None
		old_parent: DF.Link | None
		parent_warehouse: DF.Link | None
		phone_no: DF.Data | None
		pin: DF.Data | None
		rgt: DF.Int
		state: DF.Data | None
		warehouse_name: DF.Data
		warehouse_type: DF.Link | None
	# end: auto-generated types

	nsm_parent_field = "parent_warehouse"

	def autoname(self):
		if self.company:
			suffix = " - " + frappe.get_cached_value("Company", self.company, "abbr")
			if not self.warehouse_name.endswith(suffix):
				self.name = self.warehouse_name + suffix
				return

		self.name = self.warehouse_name

	def onload(self):
		if self.company and cint(frappe.db.get_value("Company", self.company, "enable_perpetual_inventory")):
			account = self.account or get_warehouse_account(self)

			if account:
				self.set_onload("account", account)
		load_address_and_contact(self)
		self.set_onload("stock_exists", self.check_if_sle_exists(non_cancelled_only=True))

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

	def check_if_sle_exists(self, non_cancelled_only=False):
		filters = {"warehouse": self.name}
		if non_cancelled_only:
			filters["is_cancelled"] = 0
		return frappe.db.exists("Stock Ledger Entry", filters)

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
def get_children(doctype, parent=None, company=None, is_root=False, include_disabled=False):
	if is_root:
		parent = ""

	if isinstance(include_disabled, str):
		include_disabled = json.loads(include_disabled)

	fields = ["name as value", "is_group as expandable"]

	filters = [
		[IfNull(Field("parent_warehouse"), ""), "=", parent],
		["company", "in", (company, None, "")],
	]

	if frappe.db.has_column(doctype, "disabled") and not include_disabled:
		filters.append(["disabled", "=", False])

	return frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")


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


@request_cache
def get_child_warehouses(warehouse):
	from frappe.utils.nestedset import get_descendants_of

	children = get_descendants_of("Warehouse", warehouse, ignore_permissions=True, order_by="lft")
	return [*children, warehouse]  # append self for backward compatibility


def get_warehouses_based_on_account(account, company=None):
	warehouses = []
	for d in frappe.get_all(
		"Warehouse", fields=["name", "is_group"], filters={"account": account, "disabled": 0}
	):
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
	if not (warehouses := filters.get("warehouse")):
		return query

	warehouse_table = frappe.qb.DocType("Warehouse")

	if isinstance(warehouses, str):
		warehouses = [warehouses]

	warehouse_range = frappe.get_all(
		"Warehouse",
		filters={
			"name": ("in", warehouses),
		},
		fields=["lft", "rgt"],
		as_list=True,
	)

	child_query = frappe.qb.from_(warehouse_table).select(warehouse_table.name)

	range_conditions = [
		(warehouse_table.lft >= lft) & (warehouse_table.rgt <= rgt) for lft, rgt in warehouse_range
	]

	combined_condition = range_conditions[0]
	for condition in range_conditions[1:]:
		combined_condition = combined_condition | condition

	child_query = child_query.where(combined_condition).where(warehouse_table.name == sle.warehouse)

	query = query.where(ExistsCriterion(child_query))

	return query


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_warehouses_for_reorder(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe._dict(filters or {})

	if filters.warehouse and not frappe.db.exists("Warehouse", filters.warehouse):
		frappe.throw(_("Warehouse {0} does not exist").format(filters.warehouse))

	doctype = frappe.qb.DocType("Warehouse")

	warehouses = (
		frappe.qb.from_(doctype)
		.select(doctype.name)
		.where(doctype.disabled == 0)
		.where((doctype.is_group == 1) | (doctype.name == filters.warehouse))
		.orderby(doctype.name)
		.run(as_list=True)
	)

	return warehouses
