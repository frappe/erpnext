# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document

class TimeLogBatch(Document):

	def validate(self):
		self.set_status()
		self.doc.total_hours = 0.0
		for d in self.doclist.get({"doctype":"Time Log Batch Detail"}):
			tl = frappe.doc("Time Log", d.time_log)
			self.update_time_log_values(d, tl)
			self.validate_time_log_is_submitted(tl)
			self.doc.total_hours += float(tl.hours or 0.0)

	def update_time_log_values(self, d, tl):
		d.fields.update({
			"hours": tl.hours,
			"activity_type": tl.activity_type,
			"created_by": tl.owner
		})

	def validate_time_log_is_submitted(self, tl):
		if tl.status != "Submitted" and self.doc.docstatus == 0:
			frappe.msgprint(_("Time Log must have status 'Submitted'") + \
				" :" + tl.name + " (" + _(tl.status) + ")", raise_exception=True)
	
	def set_status(self):
		self.doc.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[str(self.doc.docstatus or 0)]
		
		if self.doc.sales_invoice:
			self.doc.status = "Billed"
	
	def on_submit(self):
		self.update_status(self.doc.name)

	def before_cancel(self):
		self.update_status(None)

	def before_update_after_submit(self):
		self.update_status(self.doc.name)

	def update_status(self, time_log_batch):
		self.set_status()
		for d in self.doclist.get({"doctype":"Time Log Batch Detail"}):
			tl = frappe.bean("Time Log", d.time_log)
			tl.doc.time_log_batch = time_log_batch
			tl.doc.sales_invoice = self.doc.sales_invoice
			tl.update_after_submit()