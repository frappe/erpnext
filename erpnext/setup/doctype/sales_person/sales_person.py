# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet

class SalesPerson(NestedSet):
	nsm_parent_field = 'parent_sales_person';

	def validate(self):
		for d in self.get('targets') or []:
			if not flt(d.target_qty) and not flt(d.target_amount):
				frappe.throw(_("Either target qty or target amount is mandatory."))
		self.validate_employee_id()

	def on_update(self):
		super(SalesPerson, self).on_update()
		self.validate_one_root()

	def get_email_id(self):
		if self.employee:
			user = frappe.db.get_value("Employee", self.employee, "user_id")
			if not user:
				frappe.throw(_("User ID not set for Employee {0}").format(self.employee))
			else:
				return frappe.db.get_value("User", user, "email") or user

	def validate_employee_id(self):
		sales_person = frappe.db.get_value("Sales Person", {"employee": self.employee})
		
		if sales_person and sales_person != self.name:
			frappe.throw(_("Another Sales Person {0} exists with the same Employee id").format(sales_person))
