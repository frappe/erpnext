# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from typing import Any

import frappe
from frappe import _, throw
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.query_builder import Field
from frappe.query_builder.functions import IfNull
from frappe.utils import cint
from frappe.utils.caching import request_cache
from frappe.utils.nestedset import NestedSet
from pypika.terms import ExistsCriterion

from erpnext.stock import get_warehouse_account, get_warehouse_account_map


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
			account = self.account or get_warehouse_account(self, raise_error=False)

			if account:
				self.set_onload("account", account)
		load_address_and_contact(self)
		self.set_onload("stock_exists", self.check_if_sle_exists(non_cancelled_only=True))

	def validate(self):
		self.validate_warehouse_account()
		self.validate_inventory_account()
		self.validate_group_conversion()
		self.validate_company_change()
		self.validate_parent_warehouse()
		self.validate_disable_with_stock()
		self.warn_about_multiple_warehouse_account()

	def validate_disable_with_stock(self):
		if not self.disabled or self.is_new() or not self.has_value_changed("disabled"):
			return

		if item_code := frappe.db.get_value(
			"Bin", {"warehouse": self.name, "actual_qty": ("!=", 0)}, "item_code"
		):
			throw(
				_("Warehouse {0} cannot be disabled as stock exists for Item {1}").format(
					frappe.bold(self.name), frappe.bold(item_code)
				)
			)

	def validate_parent_warehouse(self):
		if not self.parent_warehouse:
			return

		parent = frappe.db.get_value(
			"Warehouse", self.parent_warehouse, ["is_group", "company"], as_dict=True
		)
		if not parent.is_group or (parent.company and parent.company != self.company):
			throw(
				_("Parent Warehouse {0} must be a group warehouse of Company {1}").format(
					frappe.bold(self.parent_warehouse), frappe.bold(self.company)
				)
			)

	def validate_company_change(self):
		if self.is_new() or not self.has_value_changed("company"):
			return

		if self.check_if_sle_exists() or frappe.db.exists("Bin", {"warehouse": self.name}):
			throw(
				_("Company cannot be changed for Warehouse {0} as it has stock transactions").format(
					frappe.bold(self.name)
				)
			)

		if self.check_if_child_exists():
			throw(
				_("Company cannot be changed for Warehouse {0} as it has child warehouses").format(
					frappe.bold(self.name)
				)
			)

	def validate_group_conversion(self):
		if self.is_new() or not self.has_value_changed("is_group"):
			return

		if self.is_group and self.check_if_sle_exists():
			throw(_("Warehouses with existing transaction can not be converted to group."))

		if self.is_group and (bin_with_qty := self.get_bin_with_quantity()):
			throw(
				_("Warehouse {0} can not be converted to group as quantity exists for Item {1}").format(
					self.name, bin_with_qty.item_code
				)
			)

		if self.is_group and frappe.db.exists("Item Default", {"default_warehouse": self.name}):
			throw(
				_("Warehouse {0} can not be converted to group as it is an Item's default warehouse").format(
					self.name
				)
			)

		if not self.is_group and self.check_if_child_exists():
			throw(_("Warehouses with child nodes cannot be converted to ledger"))

	def validate_warehouse_account(self):
		if not self.account:
			return

		account = frappe.get_cached_value(
			"Account", self.account, ["company", "account_type", "is_group"], as_dict=True
		)
		if self.company and account.company and account.company != self.company:
			frappe.throw(
				_("Account {0} does not belong to Company {1}").format(
					frappe.bold(self.account), frappe.bold(self.company)
				)
			)

		if account.is_group or account.account_type != "Stock":
			frappe.throw(
				_("Account {0} must be a non-group account of type Stock").format(frappe.bold(self.account))
			)

	def validate_inventory_account(self):
		if (
			not self.is_new()
			or not self.company
			or self.flags.ignore_inventory_account_validation
			or not frappe.get_cached_value("Company", self.company, "enable_perpetual_inventory")
		):
			return

		warehouse = frappe._dict(self.as_dict())
		if not self.account and self.parent_warehouse:
			parent_bounds = frappe.db.get_value(
				"Warehouse", self.parent_warehouse, ["lft", "rgt"], as_dict=True
			)
			if parent_bounds:
				warehouse.update(parent_bounds)

		get_warehouse_account(warehouse)

	def on_update(self):
		super().on_update()

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_trash(self):
		if bin_with_qty := self.get_bin_with_quantity():
			throw(
				_("Warehouse {0} can not be deleted as quantity exists for Item {1}").format(
					self.name, bin_with_qty.item_code
				)
			)

		if self.check_if_sle_exists():
			throw(_("Warehouse can not be deleted as stock ledger entry exists for this warehouse."))

		if self.check_if_child_exists():
			throw(_("Child warehouse exists for this warehouse. You can not delete this warehouse."))

		frappe.db.delete("Bin", filters={"warehouse": self.name})
		self.update_nsm_model()
		self.unlink_from_items()

	def get_bin_with_quantity(self):
		qty_fields = (
			"actual_qty",
			"reserved_qty",
			"ordered_qty",
			"indented_qty",
			"projected_qty",
			"planned_qty",
		)
		for d in frappe.get_all("Bin", fields=["item_code", *qty_fields], filters={"warehouse": self.name}):
			if any(d.get(field) for field in qty_fields):
				return d

	def warn_about_multiple_warehouse_account(self):
		"If Warehouse value is split across multiple accounts, warn."

		if not frappe.db.count("Stock Ledger Entry", {"warehouse": self.name}):
			return

		doc_before_save = self.get_doc_before_save()
		old_wh_account = doc_before_save.account if doc_before_save else None

		if self.is_new() or (self.account and old_wh_account == self.account):
			return

		frappe.msgprint(
			title=_("Warning: Account changed for warehouse"),
			indicator="orange",
			msg=_(
				"Stock entries exist with the old account. Changing the account may lead to a mismatch between the warehouse closing balance and the account closing balance. The overall closing balance will still match, but not for the specific account."
			),
			alert=True,
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
def get_children(
	doctype: str,
	parent: str | None = None,
	company: str | None = None,
	is_root: bool = False,
	include_disabled: bool | str = False,
):
	if is_root:
		parent = ""

	include_disabled = frappe.parse_json(include_disabled)

	fields = ["name as value", "is_group as expandable"]

	filters = [
		[IfNull(Field("parent_warehouse"), ""), "=", parent],
		["company", "in", (company, None, "")],
	]

	if frappe.db.has_column(doctype, "disabled") and not include_disabled:
		filters.append(["disabled", "=", False])

	return frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")


@frappe.whitelist(methods=["POST"])
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = make_tree_args(**frappe.form_dict)

	if cint(args.is_root):
		args.parent_warehouse = None

	frappe.get_doc(args).insert()


@frappe.whitelist(methods=["POST"])
def convert_to_group_or_ledger(docname: str | None = None):
	if not docname:
		docname = frappe.form_dict.docname

	# Converting a warehouse between group and ledger restructures the tree, so it needs write on
	# the warehouse being converted. `Warehouse` write is held by Item Manager alone, which is also
	# who can open the form this button sits on (warehouse.js:104).
	warehouse = frappe.get_doc("Warehouse", docname)
	warehouse.check_permission("write")

	return warehouse.convert_to_group_or_ledger()


@request_cache
def get_child_warehouses(warehouse):
	from frappe.utils.nestedset import get_descendants_of

	children = get_descendants_of("Warehouse", warehouse, ignore_permissions=True, order_by="lft")
	return [*children, warehouse]  # append self for backward compatibility


def get_warehouses_based_on_account(account, company=None):
	warehouse_account_map = get_warehouse_account_map(company)
	warehouses = [
		warehouse
		for warehouse, details in warehouse_account_map.items()
		if not details.is_group and details.account == account
	]

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
def get_warehouses_for_reorder(
	doctype: str, txt: Any, searchfield: Any, start: int, page_len: int, filters: dict
):
	# Reached from the Item form's reorder table (item.js:774); `read` on Warehouse is the target
	# right and costs none of the roles that can edit an Item.
	frappe.has_permission("Warehouse", throw=True)

	filters = frappe._dict(filters or {})

	if filters.warehouse and not frappe.db.exists("Warehouse", filters.warehouse):
		frappe.throw(_("Warehouse {0} does not exist").format(filters.warehouse))

	# get_list, not get_all: it scopes the rows the doctype check does not; `as_list` keeps the tuples the picker expects
	warehouses = frappe.get_list(
		"Warehouse",
		filters={"disabled": 0},
		or_filters=[["is_group", "=", 1], ["name", "=", filters.warehouse]],
		fields=["name"],
		order_by="name",
		as_list=True,
	)

	return warehouses
