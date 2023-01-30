# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_time, get_datetime, combine_datetime


class CustomerFeedback(Document):
	def validate(self):
		self.set_title()
		self.set_status()

	def set_title(self):
		self.title = self.customer_name or self.customer

	def set_status(self):
		if self.customer_feedback:
			self.status = "Completed"
		else:
			self.status = "Pending"


@frappe.whitelist()
def submit_customer_feedback_communication(reference_doctype, reference_name, communication_type, communication):
	if not communication:
		frappe.throw(_('Message cannot be empty'))

	if not frappe.db.exists(reference_doctype, reference_name):
		frappe.throw(_("{0} {1} does not exist".format(reference_doctype, reference_name)))

	source_doc = frappe.get_doc(reference_doctype, reference_name)
	source_doc.check_permission("read")

	filters = {
		'reference_doctype': reference_doctype,
		'reference_name': reference_name,
		'customer': source_doc.customer,
		'vehicle': source_doc.applies_to_vehicle
	}

	customer_feedback = frappe.db.get_value("Customer Feedback", filters=filters)

	if customer_feedback:
		feedback_doc = frappe.get_doc("Customer Feedback", customer_feedback)
	else:
		feedback_doc = frappe.get_doc({
			**filters,
			"doctype": "Customer Feedback",
		}).insert(ignore_permissions=True)

	cur_dt = get_datetime()
	cur_date = getdate(cur_dt)
	cur_time = get_time(cur_dt)

	if communication_type == "Feedback":
		feedback_doc.update({
			"feedback_date": cur_date,
			"feedback_time": cur_time,
			"customer_feedback": communication
		})
	else:
		feedback_doc.update({
			"contact_date": cur_date,
			"contact_time": cur_time,
			"contact_remark": communication
		})

	feedback_doc.save()

	# Add Communication
	communication_doc = frappe.get_doc({
		"doctype": "Communication",
		"reference_doctype": feedback_doc.doctype,
		"reference_name": feedback_doc.name,
		"content": communication,
		"communication_type": communication_type,
		"sent_or_received": "Received",
		"subject": "Customer Feedback" + \
			("" if communication_type=="Feedback" else " Contact Remark") + \
			" ({0}, {1})".format(source_doc.doctype, source_doc.name),
		"sender": frappe.session.user
	})

	communication_doc.append("timeline_links", {
		"link_doctype": source_doc.doctype,
		"link_name": source_doc.name,
	})

	communication_doc.append("timeline_links", {
		"link_doctype": "Customer",
		"link_name": source_doc.customer,
	})

	communication_doc.append("timeline_links", {
		"link_doctype": "Vehicle",
		"link_name": source_doc.applies_to_vehicle,
	})

	communication_doc.insert(ignore_permissions=True)

	return {
		"contact_remark": feedback_doc.get('contact_remark'),
		"customer_feedback": feedback_doc.get('customer_feedback'),
		"contact_dt": combine_datetime(feedback_doc.contact_date, feedback_doc.contact_time) if feedback_doc.get('contact_remark') else None,
		"feedback_dt": combine_datetime(feedback_doc.feedback_date, feedback_doc.feedback_time) if feedback_doc.get('customer_feedback') else None
	}
