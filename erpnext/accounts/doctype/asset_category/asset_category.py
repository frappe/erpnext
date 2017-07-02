# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
import frappe.utils.nestedset

class AssetCategory(Document):
	nsm_parent_field = 'parent_asset_category'
	
	def validate(self):
		for field in ("total_number_of_depreciations", "frequency_of_depreciation"):
			if cint(self.get(field))<1:
				frappe.throw(_("{0} must be greater than 0").format(self.meta.get_label(field)), frappe.MandatoryError)

	def on_update(self):
		self.update_nsm_model()

	def on_trash(self):
		self.validate_trash()
		self.update_nsm_model()

	def update_nsm_model(self):
		"""update lft, rgt indices for nested set model"""
		frappe.utils.nestedset.update_nsm(self)


	def validate_trash(self):
		pass