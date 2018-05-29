# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from erpnext.utilities.transaction_base import delete_events
from frappe.model.document import Document

class Department(NestedSet):
	nsm_parent_field = 'parent_department'

	def autoname(self):
		if not self.department_name==_("All Departments"):
			abbr = frappe.db.get_value('Company', self.company, 'abbr')
			self.name = '{0} - {1}'.format(self.department_name, abbr)
		else:
			self.name = self.department_name

	def validate(self):
		if not self.parent_department and self.department_name != _("All Departments") \
			and frappe.db.exists("Department", _("All Departments")):
				self.parent_department = _("All Departments")

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()

	def on_trash(self):
		super(Department, self).on_trash()
		delete_events(self.doctype, self.name)

def on_doctype_update():
	frappe.db.add_index("Department", ["lft", "rgt"])

@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	condition = ''
	if company == parent:
		condition = 'name="All Departments"'
	elif company:
		condition = "parent_department='{0}' and company='{1}'".format(parent, company)
	else:
		condition = "parent_department = '{0}'".format(parent)

	return frappe.db.sql("""
		select
			name as value,
			is_group as expandable
		from `tab{doctype}`
		where
			{condition}
		order by name""".format(doctype=doctype, condition=condition), as_dict=1)
