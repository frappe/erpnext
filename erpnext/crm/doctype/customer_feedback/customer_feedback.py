# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr
from frappe.model.mapper import get_mapped_doc
from frappe.utils import getdate, get_time, get_datetime, combine_datetime


class CustomerFeedback(Document):
	def validate(self):
		self.set_title()
		self.set_status()
		self.get_previous_values()

	def on_update(self):
		self.update_communication()

	def set_title(self):
		self.title = self.customer_name or self.customer

	def set_status(self):
		if self.customer_feedback:
			self.status = "Completed"
		else:
			self.status = "Pending"

	def get_previous_values(self):
		self.previous_values = {}
		if not self.is_new():
			self.previous_values = frappe.db.get_value(
				"Customer Feedback",
				self.name,
				["contact_remarks", "customer_feedback"],
				as_dict=True
			) or {}

	def update_communication(self):
		previous_values = self.get('previous_values') or {}
		if self.get("contact_remarks") and cstr(previous_values.get('contact_remarks')) != cstr(self.contact_remarks):
			self.create_communication("contact_remarks")

		if self.get("customer_feedback") and cstr(previous_values.get('customer_feedback')) != cstr(self.customer_feedback):
			self.create_communication("customer_feedback")

	def create_communication(self, for_field):
		subject = _("Customer Feedback") + (_(" Remarks") if for_field == "contact_remarks" else "")

		if self.reference_doctype and self.reference_name:
			subject += " ({0})".format(self.reference_name)

		communication_doc = frappe.get_doc({
			"doctype": "Communication",
			"reference_doctype": self.get('doctype'),
			"reference_name": self.get('name'),
			"content": self.get(for_field),
			"communication_type": "Feedback",
			"sent_or_received": "Received",
			"subject": subject,
			"sender": frappe.session.user
		})

		if self.reference_doctype and self.reference_name:
			communication_doc.append("timeline_links", {
				"link_doctype": self.reference_doctype,
				"link_name": self.reference_name
			})

		if self.customer:
			communication_doc.append("timeline_links", {
				"link_doctype": "Customer",
				"link_name": self.customer,
			})

		if self.applies_to_serial_no:
			communication_doc.append("timeline_links", {
				"link_doctype": "Serial No",
				"link_name": self.applies_to_serial_no,
			})

		if 'Vehicles' in frappe.get_active_domains() and self.applies_to_vehicle:
			communication_doc.append("timeline_links", {
				"link_doctype": "Vehicle",
				"link_name": self.applies_to_vehicle,
			})

		communication_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def submit_customer_feedback(reference_doctype, reference_name, feedback_or_remark, message):
	if not message:
		frappe.throw(_('Message cannot be empty'))

	if not frappe.db.exists(reference_doctype, reference_name):
		frappe.throw(_("{0} {1} does not exist".format(reference_doctype, reference_name)))

	feedback_doc = get_customer_feedback_doc(reference_doctype, reference_name)

	cur_dt = get_datetime()
	cur_date = getdate(cur_dt)
	cur_time = get_time(cur_dt)

	if feedback_or_remark == "Feedback":
		feedback_doc.update({
			"feedback_date": cur_date,
			"feedback_time": cur_time,
			"customer_feedback": message
		})
	else:
		feedback_doc.update({
			"contact_date": cur_date,
			"contact_time": cur_time,
			"contact_remarks": message
		})

	feedback_doc.save()

	return {
		"contact_remarks": feedback_doc.get('contact_remarks'),
		"customer_feedback": feedback_doc.get('customer_feedback'),
		"contact_dt": combine_datetime(feedback_doc.contact_date, feedback_doc.contact_time)
			if feedback_doc.get('contact_remarks') else None,
		"feedback_dt": combine_datetime(feedback_doc.feedback_date, feedback_doc.feedback_time)
			if feedback_doc.get('customer_feedback') else None
	}


def get_customer_feedback_doc(reference_doctype, reference_name):
	filters = {
		'reference_doctype': reference_doctype,
		'reference_name': reference_name
	}

	customer_feedback = frappe.db.get_value("Customer Feedback", filters=filters)

	if customer_feedback:
		feedback_doc = frappe.get_doc("Customer Feedback", customer_feedback)
	else:
		feedback_doc = get_mapped_doc(reference_doctype, reference_name, {
			reference_doctype: {
				"doctype": "Customer Feedback",
				"field_map": {
					"doctype": "reference_doctype",
					"name": "reference_name"
				}
			},
		})

	return feedback_doc
