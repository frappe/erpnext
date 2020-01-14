# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.utils.nestedset import NestedSet
import frappe

class HealthcareServiceUnit(NestedSet):
	nsm_parent_field = 'parent_healthcare_service_unit'

	def autoname(self):
		if self.company:
			suffix = " - " + frappe.get_cached_value('Company',  self.company,  "abbr")
			if not self.healthcare_service_unit_name.endswith(suffix):
				self.name = self.healthcare_service_unit_name + suffix
		else:
			self.name = self.healthcare_service_unit_name

	def on_update(self):
		super(HealthcareServiceUnit, self).on_update()
		self.validate_one_root()

	def validate(self):
		if self.is_group == 1:
			self.allow_appointments = 0
			self.overlap_appointments = 0
			self.inpatient_occupancy = 0
		elif self.allow_appointments != 1:
			self.overlap_appointments = 0
