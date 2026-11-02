# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.utils.nestedset import NestedSet, get_root_of

from erpnext.utilities.transaction_base import delete_events


class Department(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link
		department_name: DF.Data
		disabled: DF.Check
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Data | None
		parent_department: DF.Link | None
		rgt: DF.Int
	# end: auto-generated types

	nsm_parent_field = "parent_department"

	def autoname(self):
		if self.company:
			self.name = get_abbreviated_name(self.department_name, self.company)
		else:
			self.name = self.department_name

	def validate(self):
		if not self.parent_department:
			root = get_root_of("Department")
			if root:
				self.parent_department = root

	def before_rename(self, old, new, merge=False):
		# renaming consistency with abbreviation
		if frappe.get_cached_value("Company", self.company, "abbr") not in new:
			new = get_abbreviated_name(new, self.company)

		return new

	def on_update(self):
		if not (frappe.local.flags.ignore_update_nsm or frappe.flags.in_setup_wizard):
			super().on_update()

	def on_trash(self):
		super().on_trash()
		delete_events(self.doctype, self.name)


def on_doctype_update():
	frappe.db.add_index("Department", ["lft", "rgt"])


def get_abbreviated_name(name, company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	new_name = f"{name} - {abbr}"
	return new_name


@frappe.whitelist()
def get_children(
	doctype: str,
	parent: str | None = None,
	company: str | None = None,
	is_root: bool = False,
	include_disabled: str | dict | None = None,
):
	include_disabled = frappe.parse_json(include_disabled)
	fields = ["name as value", "is_group as expandable"]
	filters = {}

	if company == parent:
		filters["name"] = get_root_of("Department")
	elif company:
		filters["parent_department"] = parent
		filters["company"] = company
	else:
		filters["parent_department"] = parent

	# `doctype` is caller-supplied and only ever reaches has_column here; the query below is fixed to
	# Department, so pin it rather than letting a caller probe another table's columns.
	if frappe.db.has_column("Department", "disabled") and not include_disabled:
		filters["disabled"] = False

	# get_list, not get_all: it applies the caller's Department permission and their User
	# Permissions. Department carries no `if_owner` row, so this does not silently empty the tree —
	# the same check made before swapping the call in setup/doctype/company/company.py.
	return frappe.get_list("Department", fields=fields, filters=filters, order_by="name")


@frappe.whitelist(methods=["POST"])
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	# `args` comes straight from form_dict, so without this the caller chooses the doctype that gets
	# created. insert() would still check permissions on whatever they named, but the Department
	# tree's add-node action is not meant to build anything else.
	args.doctype = "Department"

	if args.parent_department == args.company:
		args.parent_department = None

	frappe.get_doc(args).insert()
