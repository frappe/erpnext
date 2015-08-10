# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

class QualityReport8D(Document):
	def validate(self):
		self.set_action_type()
		
		if self.status=="Closed" and not self.date_of_closure:
			self.date_of_closure = today()
		
	def set_action_type(self):
		for action in self.get("containment_actions"):
			action.action_type = "Containment"

		for action in self.get("corrective_actions"):
			action.action_type = "Corrective"