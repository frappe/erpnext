# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class MedicalExamination(Document):
	def validate(self):
		if u'HR Manager' in frappe.get_roles(frappe.session.user) or u'HR User' in frappe.get_roles(frappe.session.user):
			if not self.destination :
				frappe.throw(_("Destination Missing"))
			if not self.message :
				frappe.throw(_("Message Missing"))
			#if not self.approver :
			#	frappe.throw(_("Approver Missing"))
