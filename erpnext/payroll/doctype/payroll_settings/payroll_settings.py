# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe import _

class PayrollSettings(Document):
	def validate(self):
		self.validate_password_policy()

		if not self.daily_wages_fraction_for_half_day:
			self.daily_wages_fraction_for_half_day = 0.5

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
