# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class SoilTexture(Document):
	soil_edit_order = [2, 1, 0]
	soil_types = ['clay_composition', 'sand_composition', 'silt_composition']

	@frappe.whitelist()
	def load_contents(self):
		docs = frappe.get_all("Agriculture Analysis Criteria", filters={'linked_doctype':'Soil Texture'})
		for doc in docs:
			self.append('soil_texture_criteria', {'title': str(doc.name)})

	def validate(self):
		self.update_soil_edit('sand_composition')
		for soil_type in self.soil_types:
			if self.get(soil_type) > 100 or self.get(soil_type) < 0:
				frappe.throw(_("{0} should be a value between 0 and 100").format(soil_type))
		if sum(self.get(soil_type) for soil_type in self.soil_types) != 100:
			frappe.throw(_('Soil compositions do not add up to 100'))

	@frappe.whitelist()
	def update_soil_edit(self, soil_type):
		self.soil_edit_order[self.soil_types.index(soil_type)] = max(self.soil_edit_order)+1
		self.soil_type = self.get_soil_type()

	def get_soil_type(self):
		# update the last edited soil type
		if sum(self.soil_edit_order) < 5: return
		last_edit_index = self.soil_edit_order.index(min(self.soil_edit_order))

		# set composition of the last edited soil
		self.set(self.soil_types[last_edit_index],
			100 - sum(cint(self.get(soil_type)) for soil_type in self.soil_types) + cint(self.get(self.soil_types[last_edit_index])))

		# calculate soil type
		c, sa, si = flt(self.clay_composition), flt(self.sand_composition), flt(self.silt_composition)

		if si + (1.5 * c) < 15:
			return 'Sand'
		elif si + 1.5 * c >= 15 and si + 2 * c < 30:
			return 'Loamy Sand'
		elif ((c >= 7 and c < 20) or (sa > 52) and ((si + 2*c) >= 30) or (c < 7 and si < 50 and (si+2*c) >= 30)):
			return 'Sandy Loam'
		elif ((c >= 7 and c < 27) and (si >= 28 and si < 50) and (sa <= 52)):
			return 'Loam'
		elif ((si >= 50 and (c >= 12 and c < 27)) or ((si >= 50 and si < 80) and c < 12)):
			return 'Silt Loam'
		elif (si >= 80 and c < 12):
			return 'Silt'
		elif ((c >= 20 and c < 35) and (si < 28) and (sa > 45)):
			return 'Sandy Clay Loam'
		elif ((c >= 27 and c < 40) and (sa > 20 and sa <= 45)):
			return 'Clay Loam'
		elif ((c >= 27 and c < 40) and (sa  <= 20)):
			return 'Silty Clay Loam'
		elif (c >= 35 and sa > 45):
			return 'Sandy Clay'
		elif (c >= 40 and si >= 40):
			return 'Silty Clay'
		elif (c >= 40 and sa <= 45 and si < 40):
			return 'Clay'
		else:
			return 'Select'
