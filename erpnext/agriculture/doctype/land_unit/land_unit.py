# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
# from frappe.utils import flt
from frappe.utils.nestedset import NestedSet

land_unit_types=['Farm or Estate Master','Division Master','Field Master','	Block']

class LandUnit(NestedSet):
	nsm_parent_field='parent_land_unit'

	def validate(self):
		doc_parent=frappe.get_doc('Land Unit', self.get('parent'))
		# frappe.msgprint(str(doc_parent.get('land_unit_type')))
		if str(doc_parent.get('parent')):
			# frappe.msgprint(str(doc_parent.get('parent')))
			self.land_unit_type=land_unit_types[land_unit_types.index(str(doc_parent.get('land_unit_type')))+1]
		else:
			self.land_unit_type='Farm or Estate Master'
		# frappe.msgprint(land_unit_types[land_unit_types.index(doc_parent.get('parent'))+1])

		self.location='<!DOCTYPE html><html><head><title></title></head><body><h1>fdlskfjlsdkf</h1></body></html>'

	def on_update(self):
		super(LandUnit, self).on_update()
		self.validate_one_root()
