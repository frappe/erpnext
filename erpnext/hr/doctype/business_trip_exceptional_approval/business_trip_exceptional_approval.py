# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class BusinessTripExceptionalApproval(Document):
	def on_submit(self):
		if self.status=='Pending':
			frappe.throw(_("Please change the status before sumbit"))
		else:
			if self.status =="Approved":
				state = 'Approved By Requester Director'
			else:
				state = 'Rejected By Requester Director'
				self.docstatus = 2

			doc = frappe.get_doc('Business Trip', self.business_trip )
			doc.workflow_state = state
			doc.save(ignore_permissions=True)
		
		 	# self.status=='Approved':

		# 	doc = frappe.get_doc('Business Trip', self.business_trip )
		# 	doc.workflow_state = 'Approved By Requester Director'
		# 	doc.flags.ignore_mandatory = True
		# 	doc.save()
		# elif self.status=='Rejected':
		# 	doc = frappe.get_doc('Business Trip', self.business_trip )
		# 	doc.workflow_state = 'Rejected By Requester Director'
		# 	doc.docstatus = 2
		# 	doc.flags.ignore_mandatory = True
		# 	doc.save()
		
		

		