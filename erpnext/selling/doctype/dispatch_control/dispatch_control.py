# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DispatchControl(Document):	
	def validate(self):
		self.verified_state()
		
		if self.docstatus == 0:
			self.status = "Draft"

	def verified_state(self):
		if self.docstatus == 1 and self.ready < 100 and self.unready < 100:
			self.status = "To Ready and Unready"
			self.db_set('status', "To Ready and Unready", update_modified=False)
		if self.docstatus == 1 and self.ready < 100 and self.unready >= 100:
			self.status = "To Unready"
			self.db_set('status', "To Unready", update_modified=False)
		if self.docstatus == 1 and self.ready == 100 and self.unready < 100:
			self.status = "Delivered"
			self.db_set('status', "Delivered", update_modified=False)

	def on_update(self):
		self.porcent()
		
	
	def porcent(self):
		products_ready = frappe.get_all("Dispatch Control Detail", ["name"], filters = {"ready": 1, "parent": self.name})

		products_unready = frappe.get_all("Dispatch Control Detail", ["name"], filters = {"ready": 0, "parent": self.name})

		total_products = len(products_ready) + len(products_unready)

		porcent_ready = len(products_ready)/total_products * 100

		porcent_unready = len(products_unready)/total_products * 100

		self.ready = porcent_ready
		self.db_set('ready', porcent_ready, update_modified=False)

		self.unready = porcent_unready
		self.db_set('unready', porcent_unready, update_modified=False)