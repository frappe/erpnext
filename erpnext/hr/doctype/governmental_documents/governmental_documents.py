# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class GovernmentalDocuments(Document):
	def validate(self):
		self.validate_dates()
		# self.validate_notification_message()
		# self.hooked_validate_notification_message()

	def validate_dates(self):
		from frappe.utils import getdate
		for d in self.get('governmental_documents'):
			if getdate(d.issue_date) > getdate(d.expired_date):
				frappe.throw(_("Issue Date must be smaller than expired date"))

	def validate_notification_message(self):
		from frappe.utils import getdate, add_months, nowdate
		message_hold = ""
		self.is_message = 0
		for d in self.get('governmental_documents'):
			if getdate(d.expired_date) <= getdate(add_months(nowdate(), 2)):
				message_hold += "<h5>The expired date of {0} will be expired on {1}</h5><br />".format(d.document_name, d.expired_date)
				self.is_message = 1
		self.message = message_hold

def hooked_validate_notification_message():
	from frappe.utils import getdate, add_months, nowdate
	gds  = frappe.get_all("Governmental Documents")
	if gds:
		for gd in gds:
			gdd = frappe.get_doc("Governmental Documents", gd.name)
			message_hold = ""
			gdd.is_message = 0
			for gdtab in gdd.get("governmental_documents"):
					if getdate(gdtab.expired_date) <= getdate(add_months(nowdate(), 2)):
						message_hold += "<h5>The expired date of {0} will be expired on {1}</h5><br />".format(gdtab.document_name, gdtab.expired_date)
						gdd.is_message = 1

			if gdd.message != message_hold:
				gdd.message = message_hold
				gdd.save(ignore_permissions=True)
				frappe.db.commit()