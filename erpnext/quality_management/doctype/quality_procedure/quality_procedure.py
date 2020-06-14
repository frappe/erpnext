# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.nestedset import NestedSet
from frappe import _

class QualityProcedure(NestedSet):
	nsm_parent_field = 'parent_quality_procedure'

	def before_save(self):
		for process in self.processes:
			if process.procedure:
				doc = frappe.get_doc("Quality Procedure", process.procedure)
				if doc.parent_quality_procedure:
					frappe.throw(_("{0} already has a Parent Procedure {1}.".format(process.procedure, doc.parent_quality_procedure)))
				self.is_group = 1

	def on_update(self):
		self.set_parent()

	def after_insert(self):
		self.set_parent()

	def on_trash(self):
		if self.parent_quality_procedure:
			doc = frappe.get_doc("Quality Procedure", self.parent_quality_procedure)
			for process in doc.processes:
				if process.procedure == self.name:
					doc.processes.remove(process)
					doc.save(ignore_permissions=True)

			flag_is_group = 0
			doc.load_from_db()

			for process in doc.processes:
				flag_is_group = 1 if process.procedure else 0

			doc.is_group = 0 if flag_is_group == 0 else 1
			doc.save(ignore_permissions=True)

	def set_parent(self):
		for process in self.processes:
			if process.procedure:
				doc = frappe.get_doc("Quality Procedure", process.procedure)
				doc.parent_quality_procedure = self.name
				doc.save(ignore_permissions=True)

@frappe.whitelist()
def get_children(doctype, parent=None, parent_quality_procedure=None, is_root=False):
	if parent is None or parent == "All Quality Procedures":
		parent = ""

	return frappe.db.sql("""
		select
			name as value,
			is_group as expandable
		from
			`tab{doctype}`
		where
			ifnull(parent_quality_procedure, "")={parent}
		""".format(
			doctype = doctype,
			parent=frappe.db.escape(parent)
		), as_dict=1)

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_quality_procedure == 'All Quality Procedures':
		args.parent_quality_procedure = None

	frappe.get_doc(args).insert()