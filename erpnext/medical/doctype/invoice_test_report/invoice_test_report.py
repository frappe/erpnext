# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import time
from frappe.utils import cstr

class InvoiceTestReport(Document):
	# autoname : invoice-patient(age/sex)
	def autoname(self):
		self.name = " ".join(filter(None,
			[cstr(self.get(f)).strip() for f in ["invoice", "patient"]]))

		self.name = self.name + " ("+str(self.patient_sex)+") "

@frappe.whitelist()
def mark_as_completed(status, name):
	frappe.db.set_value("Invoice Test Report", name, "status", "Completed")
