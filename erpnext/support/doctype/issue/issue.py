# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe import utils
from frappe.model.document import Document
from frappe.utils import now_datetime
from datetime import datetime, timedelta
from frappe.model.mapper import get_mapped_doc
from frappe.utils.user import is_website_user
from frappe.email.inbox import link_communication_to_document

class Issue(Document):
	def get_feed(self):
		return "{0}: {1}".format(_(self.status), self.subject)

	def validate(self):
		if self.is_new() and self.via_customer_portal:
			self.flags.create_communication = True

		if not self.raised_by:
			self.raised_by = frappe.session.user

		self.set_lead_contact(self.raised_by)

	def on_update(self):
		# Add a communication in the issue timeline
		if self.flags.create_communication and self.via_customer_portal:
			self.create_communication()
			self.flags.communication_created = None

	def set_lead_contact(self, email_id):
		import email.utils

		email_id = email.utils.parseaddr(email_id)[1]
		if email_id:
			if not self.lead:
				self.lead = frappe.db.get_value("Lead", {"email_id": email_id})

			if not self.contact and not self.customer:
				self.contact = frappe.db.get_value("Contact", {"email_id": email_id})

				if self.contact:
					contact = frappe.get_doc("Contact", self.contact)
					self.customer = contact.get_link_for("Customer")

			if not self.company:
				self.company = frappe.db.get_value("Lead", self.lead, "company") or \
					frappe.db.get_default("Company")

	def create_communication(self):
		communication = frappe.new_doc("Communication")
		communication.update({
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Received",
			"email_status": "Open",
			"subject": self.subject,
			"sender": self.raised_by,
			"content": self.description,
			"status": "Linked",
			"reference_doctype": "Issue",
			"reference_name": self.name
		})
		communication.ignore_permissions = True
		communication.ignore_mandatory = True
		communication.save()

	@frappe.whitelist()
	def split_issue(self, subject, communication_id):
		# Bug: Pressing enter doesn't send subject
		from copy import deepcopy

		replicated_issue = deepcopy(self)
		replicated_issue.subject = subject
		replicated_issue.issue_split_from = self.name
		replicated_issue.first_response_time = 0
		replicated_issue.first_responded_on = None
		replicated_issue.creation = now_datetime()

		# Reset SLA
		if replicated_issue.service_level_agreement:
			replicated_issue.service_level_agreement_creation = now_datetime()
			replicated_issue.service_level_agreement = None
			replicated_issue.agreement_status = "Ongoing"
			replicated_issue.response_by = None
			replicated_issue.response_by_variance = None
			replicated_issue.resolution_by = None
			replicated_issue.resolution_by_variance = None
			replicated_issue.reset_issue_metrics()

		frappe.get_doc(replicated_issue).insert()

		# Replicate linked Communications
		# TODO: get all communications in timeline before this, and modify them to append them to new doc
		comm_to_split_from = frappe.get_doc("Communication", communication_id)
		communications = frappe.get_all("Communication",
			filters={"reference_doctype": "Issue",
				"reference_name": comm_to_split_from.reference_name,
				"creation": (">=", comm_to_split_from.creation)})

		for communication in communications:
			doc = frappe.get_doc("Communication", communication.name)
			doc.reference_name = replicated_issue.name
			doc.save(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Issue",
			"reference_name": replicated_issue.name,
			"content": " - Split the Issue from <a href='/app/Form/Issue/{0}'>{1}</a>".format(self.name, frappe.bold(self.name)),
		}).insert(ignore_permissions=True)

		return replicated_issue.name

def get_list_context(context=None):
	return {
		"title": _("Issues"),
		"get_list": get_issue_list,
		"row_template": "templates/includes/issue_row.html",
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True
	}


def get_issue_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
	from frappe.www.list import get_list

	user = frappe.session.user
	contact = frappe.db.get_value("Contact", {"user": user}, "name")
	customer = None

	if contact:
		contact_doc = frappe.get_doc("Contact", contact)
		customer = contact_doc.get_link_for("Customer")

	ignore_permissions = False
	if is_website_user():
		if not filters: filters = {}

		if customer:
			filters["customer"] = customer
		else:
			filters["raised_by"] = user

		ignore_permissions = True

	return get_list(doctype, txt, filters, limit_start, limit_page_length, ignore_permissions=ignore_permissions)


@frappe.whitelist()
def set_multiple_status(names, status):

	for name in json.loads(names):
		frappe.db.set_value("Issue", name, "status", status)

@frappe.whitelist()
def set_status(name, status):
	frappe.db.set_value("Issue", name, "status", status)

def auto_close_tickets():
	"""Auto-close replied support tickets after 7 days"""
	auto_close_after_days = frappe.db.get_value("Support Settings", "Support Settings", "close_issue_after_days") or 7

	issues = frappe.db.sql(""" select name from tabIssue where status='Replied' and
		modified<DATE_SUB(CURDATE(), INTERVAL %s DAY) """, (auto_close_after_days), as_dict=True)

	for issue in issues:
		doc = frappe.get_doc("Issue", issue.get("name"))
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()

def has_website_permission(doc, ptype, user, verbose=False):
	from erpnext.controllers.website_list_for_contact import has_website_permission
	permission_based_on_customer = has_website_permission(doc, ptype, user, verbose)

	return permission_based_on_customer or doc.raised_by==user

def update_issue(contact, method):
	"""Called when Contact is deleted"""
	frappe.db.sql("""UPDATE `tabIssue` set contact='' where contact=%s""", contact.name)

@frappe.whitelist()
def make_task(source_name, target_doc=None):
	return get_mapped_doc("Issue", source_name, {
		"Issue": {
			"doctype": "Task"
		}
	}, target_doc)

@frappe.whitelist()
def make_issue_from_communication(communication, ignore_communication_links=False):
	""" raise a issue from email """

	doc = frappe.get_doc("Communication", communication)
	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": doc.subject,
		"communication_medium": doc.communication_medium,
		"raised_by": doc.sender or "",
		"raised_by_phone": doc.phone_no or ""
	}).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Issue", issue.name, ignore_communication_links)

	return issue.name

def get_holidays(holiday_list_name):
	holiday_list = frappe.get_cached_doc("Holiday List", holiday_list_name)
	holidays = [holiday.holiday_date for holiday in holiday_list.holidays]
	return holidays