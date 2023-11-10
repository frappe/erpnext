# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class QualityProcedure(NestedSet):
	nsm_parent_field = "parent_quality_procedure"

	def before_save(self):
		self.check_for_incorrect_child()

	def on_update(self):
		NestedSet.on_update(self)
		self.set_parent()
		self.remove_parent_from_old_child()
		self.add_child_to_parent()
		self.remove_child_from_old_parent()

	def after_insert(self):
		self.set_parent()
		self.add_child_to_parent()

	def on_trash(self):
		# clear from child table (sub procedures)
		frappe.db.sql(
			"""update `tabQuality Procedure Process`
			set `procedure`='' where `procedure`=%s""",
			self.name,
		)
		NestedSet.on_trash(self, allow_root_deletion=True)

	def check_for_incorrect_child(self):
		for process in self.processes:
			if process.procedure:
				self.is_group = 1
				# Check if any child process belongs to another parent.
				parent_quality_procedure = frappe.db.get_value(
					"Quality Procedure", process.procedure, "parent_quality_procedure"
				)
				if parent_quality_procedure and parent_quality_procedure != self.name:
					frappe.throw(
						_("{0} already has a Parent Procedure {1}.").format(
							frappe.bold(process.procedure), frappe.bold(parent_quality_procedure)
						),
						title=_("Invalid Child Procedure"),
					)

	def set_parent(self):
		"""Set `Parent Procedure` in `Child Procedures`"""

		for process in self.processes:
			if process.procedure:
				if not frappe.db.get_value("Quality Procedure", process.procedure, "parent_quality_procedure"):
					frappe.db.set_value(
						"Quality Procedure", process.procedure, "parent_quality_procedure", self.name
					)

	def remove_parent_from_old_child(self):
		"""Remove `Parent Procedure` from `Old Child Procedures`"""

		if old_doc := self.get_doc_before_save():
			if old_child_procedures := set([d.procedure for d in old_doc.processes if d.procedure]):
				current_child_procedures = set([d.procedure for d in self.processes if d.procedure])

				if removed_child_procedures := list(old_child_procedures.difference(current_child_procedures)):
					for child_procedure in removed_child_procedures:
						frappe.db.set_value("Quality Procedure", child_procedure, "parent_quality_procedure", None)

	def add_child_to_parent(self):
		"""Add `Child Procedure` to `Parent Procedure`"""

		if self.parent_quality_procedure:
			parent = frappe.get_doc("Quality Procedure", self.parent_quality_procedure)
			if not [d for d in parent.processes if d.procedure == self.name]:
				parent.append("processes", {"procedure": self.name, "process_description": self.name})
				parent.save()

	def remove_child_from_old_parent(self):
		"""Remove `Child Procedure` from `Old Parent Procedure`"""

		if old_doc := self.get_doc_before_save():
			if old_parent := old_doc.parent_quality_procedure:
				if self.parent_quality_procedure != old_parent:
					parent = frappe.get_doc("Quality Procedure", old_parent)
					for process in parent.processes:
						if process.procedure == self.name:
							parent.remove(process)
					parent.save()


@frappe.whitelist()
def get_children(doctype, parent=None, parent_quality_procedure=None, is_root=False):
	if parent is None or parent == "All Quality Procedures":
		parent = ""

	if parent:
		parent_procedure = frappe.get_doc("Quality Procedure", parent)
		# return the list in order
		return [
			dict(
				value=d.procedure, expandable=frappe.db.get_value("Quality Procedure", d.procedure, "is_group")
			)
			for d in parent_procedure.processes
			if d.procedure
		]
	else:
		return frappe.get_all(
			"Quality Procedure",
			fields=["name as value", "is_group as expandable"],
			filters=dict(parent_quality_procedure=parent),
			order_by="name asc",
		)


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_quality_procedure == "All Quality Procedures":
		args.parent_quality_procedure = None

	return frappe.get_doc(args).insert()
