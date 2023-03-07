# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from master.master.doctype.employee.employee import Employee

from erpnext.utilities.transaction_base import delete_events


class ERPNextEmployee(Employee):
	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Active", "Inactive", "Suspended", "Left"])
		super(ERPNextEmployee, self).validate()

	def on_trash(self):
		super(ERPNextEmployee, self).on_trash()
		delete_events(self.doctype, self.name)
