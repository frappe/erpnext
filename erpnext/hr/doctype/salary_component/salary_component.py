# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists

class SalaryComponent(Document):
	def validate(self):
		self.validate_abbr()

	def validate_abbr(self):
		if not self.salary_component_abbr:
			self.salary_component_abbr = ''.join([c[0] for c in
				self.salary_component.split()]).upper()

		self.salary_component_abbr = self.salary_component_abbr.strip()
		self.salary_component_abbr = append_number_if_name_exists('Salary Component', self.salary_component_abbr,
			'salary_component_abbr', separator='_', filters={"name": ["!=", self.name]})

	def calculate_tax(self, annual_earning):
		taxable_amount = 0
		for slab in self.taxable_salary_slabs:
			if annual_earning > slab.from_amount and annual_earning < slab.to_amount:
				taxable_amount += (annual_earning - slab.from_amount) * slab.percent_deduction *.01
			elif annual_earning > slab.from_amount and annual_earning > slab.to_amount:
				taxable_amount += (slab.to_amount - slab.from_amount) * slab.percent_deduction * .01
		return taxable_amount
