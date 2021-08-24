# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.nestedset import NestedSet, get_root_of
from erpnext.utilities.transaction_base import delete_events
from frappe.model.document import Document

class Department(NestedSet):
	nsm_parent_field = 'parent_department'

	def autoname(self):
		root = get_root_of("Department")
		if root and self.department_name != root:
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
		if not frappe.get_cached_value('Company',  self.company,  'abbr') in new:
			new = get_abbreviated_name(new, self.company)

		return new

	def on_update(self):
		if not frappe.local.flags.ignore_update_nsm:
			super(Department, self).on_update()

	def on_trash(self):
		super(Department, self).on_trash()
		delete_events(self.doctype, self.name)

def on_doctype_update():
	frappe.db.add_index("Department", ["lft", "rgt"])

def get_abbreviated_name(name, company):
	abbr = frappe.get_cached_value('Company',  company,  'abbr')
	new_name = '{0} - {1}'.format(name, abbr)
	return new_name

@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	condition = ''
	var_dict = {
		"name": get_root_of("Department"),
		"parent": parent,
		"company": company,
	}
	if company == parent:
		condition = "name=%(name)s"
	elif company:
		condition = "parent_department=%(parent)s and company=%(company)s"
	else:
		condition = "parent_department = %(parent)s"

	return frappe.db.sql("""
		select
			name as value,
			is_group as expandable
		from `tab{doctype}`
		where
			{condition}
		order by name""".format(doctype=doctype, condition=condition), var_dict, as_dict=1)

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_department == args.company:
		args.parent_department = None

	frappe.get_doc(args).insert()
