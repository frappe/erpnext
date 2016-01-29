# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

class ProjectSettings(Document):		
	def on_update(self):
		self.toggle_simplified_time_log()
	
	def toggle_simplified_time_log(self):
		self.simplified_time_log = cint(self.simplified_time_log)

		# Make Time log property setters to hide 
		
		if self.simplified_time_log:		
			make_property_setter("Time Log", "date_worked", "hidden", not self.simplified_time_log, "Check")
			make_property_setter("Time Log", "date_worked", "reqd", self.simplified_time_log, "Check")
		else:
			make_property_setter("Time Log", "date_worked", "reqd", self.simplified_time_log, "Check")
			make_property_setter("Time Log", "date_worked", "hidden", not self.simplified_time_log, "Check")			
		
		make_property_setter("Time Log", "to_time", "hidden", self.simplified_time_log, "Check")
		make_property_setter("Time Log", "from_time", "hidden", self.simplified_time_log, "Check")
