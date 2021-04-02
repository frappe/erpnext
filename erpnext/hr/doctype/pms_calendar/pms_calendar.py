# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class PMSCalendar(Document):
	def validate(self):		  
		self.validate_dates()
			
	def validate_dates(self): 	
		if self.target_start_date > self.target_end_date:
			frappe.throw("target start date can not be greater than target end date")
		if self.review_start_date > self.review_end_date:
			frappe.throw("review start date can not be greater than review end date")
		if self.evaluation_start_date > self.evaluation_end_date:
			frappe.throw("evaluation start date can not be greater than evaluation end date") 

@frappe.whitelist()
def create_pms_extension(source_name, target_doc=None):
	doclist = get_mapped_doc("PMS Calendar", source_name, {
		"PMS Calendar": {
			"doctype": "PMS Extension",
			"field_map": {
                            "pms_calendar": "name"
                        }
		},
	}, target_doc)

	return doclist
  
   