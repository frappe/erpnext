# -*- coding: utf-8 -*-
# Copyright (c) 2017, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.utils.nestedset import NestedSet

class PatientServiceUnit(NestedSet):
	nsm_parent_field = 'parent_patient_service_unit'

	def on_update(self):
		super(PatientServiceUnit, self).on_update()
		self.validate_one_root()
