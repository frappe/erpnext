# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

class HRSettings(Document):
	def validate(self):
		self.set_naming_series()
		self.validate_password_policy()

	def set_naming_series(self):
		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Employee", "employee_number",
			self.get("emp_created_by")=="Naming Series", hide_name_field=True)

	def validate_password_policy(self):
		if self.email_salary_slip_to_employee and self.encrypt_salary_slips_in_emails:
			if not self.password_policy:
				frappe.throw(_("Password policy for Salary Slips is not set"))
	
	def on_update(self):
		self.toggle_rounded_total()
		frappe.clear_cache()

	def toggle_rounded_total(self):
		self.disable_rounded_total = cint(self.disable_rounded_total)
		make_property_setter("Salary Slip", "rounded_total", "hidden", self.disable_rounded_total, "Check")
		make_property_setter("Salary Slip", "rounded_total", "print_hide", self.disable_rounded_total, "Check")
