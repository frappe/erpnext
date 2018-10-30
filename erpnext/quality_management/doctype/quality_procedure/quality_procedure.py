# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.nestedset import NestedSet

class QualityProcedure(NestedSet):
	nsm_parent_field = 'parent_quality_procedure'
	
	def before_save(self):
		for data in self.procedure_step:
			if data.procedure == 'Procedure' and data.procedure_name != '':
				self.is_group = 1
				data.step = data.procedure_name
				doc = frappe.get_doc("Quality Procedure", data.procedure_name)
				doc.parent_quality_procedure = self.name
				doc.save()
	
	def after_insert(self):
		for data in self.procedure_step:
			if data.procedure == "Procedure":
				pass
				
	def on_trash(self):
		if(self.parent_quality_procedure):
			doc = frappe.get_doc("Quality Procedure", self.parent_quality_procedure)
			i = 0
			for data in doc.procedure_step:
				if(self.name == doc.procedure_step[i].procedure_name):
					doc.procedure_step.remove(data)
					doc.save()
				i += 1
		

@frappe.whitelist()
def get_children(doctype, parent=None, parent_quality_procedure=None, is_root=False):
	if parent == None or parent == "All Quality Procedures":
		parent = ""

	return frappe.db.sql("""
		select
			name as value,
			is_group as expandable
		from
			`tab{doctype}` comp
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