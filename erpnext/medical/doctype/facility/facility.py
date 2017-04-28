# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Facility(Document):
	def create_beds(self):
		facility = self
		try:
			start_with = int(facility.start_with)
		except Exception, e:
			frappe.throw("""Start with must be an integer""")
		try:
			no_of_beds = int(facility.num_beds)
		except Exception, e:
			frappe.throw("""Number of beds must be an integer""")
		if(no_of_beds <= 0):
			frappe.throw("""Number of beds must be greater than zero""")

		for i in range(no_of_beds):
			bed = facility.append("beds")
			bed.bed_number = start_with+i
		facility.save(ignore_permissions=True)

	def on_update(self):
		if(len(self.beds)!=self.num_beds):
			frappe.db.set_value("Facility",self.name,"num_beds",len(self.beds))
			self.reload()
