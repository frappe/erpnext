# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.utils.nestedset import NestedSet

class HealthcareServiceUnit(NestedSet):
	nsm_parent_field = 'parent_healthcare_service_unit'

	def on_update(self):
		super(HealthcareServiceUnit, self).on_update()
		self.validate_one_root()

	def validate(self):
		if self.is_group:
			self.allow_appointments = False
			self.overlap_appointments = False
		elif not self.allow_appointments:
			self.overlap_appointments = False
