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
		self.total_hours = 0.0
		for d in self.get("time_log_batch_details"):
			tl = frappe.get_doc("Time Log", d.time_log)
			self.update_time_log_values(d, tl)
			self.validate_time_log_is_submitted(tl)
			self.total_hours += float(tl.hours or 0.0)

	def update_time_log_values(self, d, tl):
		d.update({
			"hours": tl.hours,
			"activity_type": tl.activity_type,
			"created_by": tl.owner
		})

	def validate_time_log_is_submitted(self, tl):
		if tl.status != "Submitted" and self.docstatus == 0:
			frappe.throw(_("Time Log {0} must be 'Submitted'").format(tl.name))

	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[str(self.docstatus or 0)]

		if self.sales_invoice:
			self.status = "Billed"

	def on_submit(self):
		self.update_status(self.name)

	def before_cancel(self):
		self.update_status(None)

	def before_update_after_submit(self):
		self.update_status(self.name)

	def update_status(self, time_log_batch):
		self.set_status()
		for d in self.get("time_log_batch_details"):
			tl = frappe.get_doc("Time Log", d.time_log)
			tl.time_log_batch = time_log_batch
			tl.sales_invoice = self.sales_invoice
			tl.save()
