# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.nestedset import NestedSet

class Location(NestedSet):
	nsm_parent_field = 'parent_location'

	def on_update(self):
		NestedSet.on_update(self)

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		frappe.utils.nestedset.update_nsm(self)

@frappe.whitelist()
def get_children(doctype, parent=None, location=None, is_root=False):
	if parent == None or parent == "All Locations":
		parent = ""

	return frappe.db.sql("""
		select
			name as value,
			is_group as expandable
		from
			`tab{doctype}` comp
		where
			ifnull(parent_location, "")="{parent}"
		""".format(
			doctype = frappe.db.escape(doctype),
			parent=frappe.db.escape(parent)
		), as_dict=1)

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_location == 'All Locations':
		args.parent_location = None

	frappe.get_doc(args).insert()