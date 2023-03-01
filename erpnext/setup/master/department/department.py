# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from master.master.doctype.department.department import Department

from erpnext.utilities.transaction_base import delete_events


class ERPNextDepartment(Department):
	def on_trash(self):
		super(ERPNextDepartment, self).on_trash()
		delete_events(self.doctype, self.name)
