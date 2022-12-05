# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils.nestedset import NestedSet, get_root_of
from frappe.utils import cint

from erpnext.utilities.transaction_base import delete_events


class Department(NestedSet):
	nsm_parent_field = "parent_department"

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
		if not frappe.get_cached_value("Company", self.company, "abbr") in new:
			new = get_abbreviated_name(new, self.company)

		return new

	def on_update(self):
		if not (frappe.local.flags.ignore_update_nsm or frappe.flags.in_setup_wizard):
			super(Department, self).on_update()

	def on_trash(self):
		super(Department, self).on_trash()
		delete_events(self.doctype, self.name)


def on_doctype_update():
	frappe.db.add_index("Department", ["lft", "rgt"])


def get_abbreviated_name(name, company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	new_name = "{0} - {1}".format(name, abbr)
	return new_name


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	fields = ["name as value", "is_group as expandable"]
	filters = {}

	if company == parent:
		filters["name"] = get_root_of("Department")
	elif company:
		filters["parent_department"] = parent
		filters["company"] = company
	else:
		filters["parent_department"] = parent

	return frappe.get_all(doctype, fields=fields, filters=filters, order_by="name")


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_department == args.company:
		args.parent_department = None

	frappe.get_doc(args).insert()

@frappe.whitelist()
def get_employee_count(department):
	dep = frappe.get_doc("Department", department)
	cond = ''
	if cint(dep.is_department):	
		cond = ' and department ="{}"'.format(dep.name)
	if cint(dep.is_division):	
		cond = ' and division ="{}"'.format(dep.department_name)
	if cint(dep.is_unit): 
		cond = ' and unit ="{}"'.format(dep.department_name)
	if cint(dep.is_section): 
		cond = ' and section ="{}"'.format(dep.department_name)
	
	# frappe.msgprint(str(cond))
	data = {}
	if department != 'Regions - BTL':
		res = frappe.db.sql("""select count(*) employee_count from `tabEmployee`
						where status = "Active" {} """.format(cond))
		data['count'] = res[0][0]
	data['approver_name'] = dep.approver_name
	data['approver_level'] = dep.approver_level
	return data