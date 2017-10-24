# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from  frappe import _

from frappe.utils.nestedset import NestedSet
from frappe.model.document import Document

class LandUnit(NestedSet):
	#pass
	nsm_parent_field = 'parent_land_unit'

	def validate(self):
		if self.is_new():
			self.coordinates = '{{"type":"FeatureCollection","features":[{{"type":"Feature","properties":{{}},"geometry":{{"type":"Point","coordinates":[{latitude},{longitude}]}}}}]}}'.format(latitude = self.latitude, longitude = self.longitude)

	def on_update(self):
		super(LandUnit, self).on_update()
		self.validate_one_root()