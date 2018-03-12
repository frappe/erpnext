# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import scrub
from erpnext.logistics.controller.fedex_controller import FedexController

class ShippingPlan(Document):
	def __init__(self, *args, **kwargs):
		super(ShippingPlan, self).__init__(*args, **kwargs)
		self.import_controller()

	def import_controller(self):
		if self.shipper:
			controller =  "{0}Controller".format(self.shipper)
			self.controller = controller(args=self)

	def validate(self):
		self.controller.validate()

	def on_upadte(self):
		pass 