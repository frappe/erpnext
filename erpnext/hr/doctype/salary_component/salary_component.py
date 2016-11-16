# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class SalaryComponent(Document):
	def validate(self):
		self.validate_abbr()

	def validate_abbr(self):
		if not self.salary_component_abbr:
			self.salary_component_abbr = ''.join([c[0] for c in self.salary_component.split()]).upper()

		self.salary_component_abbr = self.salary_component_abbr.strip()

		if self.get('__islocal') and len(self.salary_component_abbr) > 5:
			frappe.throw(_("Abbreviation cannot have more than 5 characters"))

		if frappe.db.sql("select salary_component_abbr from `tabSalary Component` where name!=%s and salary_component_abbr=%s", (self.name, self.salary_component_abbr)):
			frappe.throw(_("Abbreviation already used for another salary component"))