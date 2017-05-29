# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DrugPrescription(Document):
	def get_quantity(self):
		quantity = 0
		dosage = None
		period = None

		if(self.dosage):
			dosage = frappe.get_doc("Prescription Dosage",self.dosage)
			for item in dosage.dosage_strength:
				quantity += item.strength
			if(self.period and self.interval):
				period = frappe.get_doc("Prescription Duration",self.period)
				if(self.interval < period.get_days()):
					quantity = quantity*(period.get_days()/self.interval)

		elif(self.interval and self.in_every and self.period):
			period = frappe.get_doc("Prescription Duration",self.period)
			interval_in = self.in_every
			if(interval_in == 'Day' and (self.interval < period.get_days())):
				quantity = period.get_days()/self.interval
			elif(interval_in == 'Hour' and (self.interval < period.get_hours())):
				quantity = period.get_hours()/self.interval
		if quantity > 0:
			return quantity
		else:
			return 1
