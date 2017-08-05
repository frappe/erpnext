# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class HealthInsuranceInfo(Document):
	
	def validate(self):
		self.validate_exp_date()

	def validate_exp_date(self):
		from frappe.utils import getdate, add_months, nowdate
		if self.expiry_date:
			if getdate(self.expiry_date) <= getdate(add_months(nowdate(), 3)):
				self.message = "<h5>The Health Insurance expiry date will be on {0}</h5>".format(self.expiry_date)
				self.is_message = 1
			else:
				self.message = ""
				self.is_message = 0

def hooked_validate_exp_date():
	from frappe.utils import getdate, add_months, nowdate
	his  = frappe.get_all("Health Insurance Info")
	if his:
		for hi in his:
			hi_doc = frappe.get_doc("Health Insurance Info", hi.name)
			hi_doc.message = ""
			hi_doc.is_message = 0
			if getdate(hi_doc.expiry_date) <= getdate(add_months(nowdate(), 2)):
				hi_doc.message = "<h5>The Health Insurance expiry date will be on {0}</h5>".format(hi_doc.expiry_date)
				hi_doc.is_message = 1
				hi_doc.save(ignore_permissions=True)
				frappe.db.commit()