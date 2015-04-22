# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.utils import flt
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class TimeLogBatch(Document):

	def validate(self):
		self.set_status()
		for d in self.get("time_logs"):
			tl = frappe.get_doc("Time Log", d.time_log)
			self.update_time_log_values(d, tl)
			self.validate_time_log_is_submitted(tl)
			self.total_hours += flt(tl.hours)
			self.total_billing_amount += flt(tl.billing_amount)

	def update_time_log_values(self, d, tl):
		d.update({
			"hours": tl.hours,
			"activity_type": tl.activity_type,
			"billing_amount": tl.billing_amount
		})

	def validate_time_log_is_submitted(self, tl):
		if tl.status == "Batched for Billing":
			frappe.throw(_("Time Log {0} already billed").format(tl.name))
		elif tl.status != "Submitted":
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
		for d in self.get("time_logs"):
			tl = frappe.get_doc("Time Log", d.time_log)
			tl.time_log_batch = time_log_batch
			tl.sales_invoice = self.sales_invoice
			tl.flags.ignore_validate_update_after_submit = True
			tl.save()

@frappe.whitelist()
def make_sales_invoice(source_name, target=None):
	def update_item(source_doc, target_doc, source_parent):
		target_doc.stock_uom = "Hour"
		target_doc.description = "via Time Logs"
		target_doc.qty = 1

	target = frappe.new_doc("Sales Invoice")
	target.append("items", get_mapped_doc("Time Log Batch", source_name, {
		"Time Log Batch": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"total_billing_amount": "rate",
				"name": "time_log_batch"
			},
			"postprocess": update_item
		}
	}))

	return target
