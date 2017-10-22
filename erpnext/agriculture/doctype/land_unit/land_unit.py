# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from  frappe import _

from frappe.utils.nestedset import NestedSet
from frappe.model.document import Document

land_unit_types=['Farm or Estate Master','Division Master','Field Master','	Block']

class LandUnit(NestedSet):
	#pass
	nsm_parent_field = 'parent_land_unit'

	def validate(self):
		if self.is_new():
			self.coordinates = '{{"type":"FeatureCollection","features":[{{"type":"Feature","properties":{{}},"geometry":{{"type":"Point","coordinates":[{latitude},{longitude}]}}}}]}}'.format(latitude = self.latitude, longitude = self.longitude)
		try:
			doc_parent = frappe.get_doc('Land Unit', self.get('parent_land_unit'))
			self.land_unit_type=land_unit_types[land_unit_types.index(str(doc_parent.get('land_unit_type')))+1]
			if self.land_unit_type == 'Block':
				self.is_group = 0
		except:
			self.land_unit_type='Farm or Estate Master'

	def on_update(self):
		super(LandUnit, self).on_update()
		self.validate_one_root()